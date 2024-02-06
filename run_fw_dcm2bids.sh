#!/bin/bash

main_dir=${HOME}/"Flywheel_Projects"

show_help=false
# Help function
show_help() {
    echo "Usage: $0 [-g value] [-p value] [-s value] [-w value] [-c value] [-pf value] -ch"
    echo "Options:"
    echo "  -g, --group           Set the name of group under Flywheel (required)"
    echo "  -p, --project         Set the name of project under Flywheel (required)"
    echo "  -s, --subject         Set the subject name under Flywheel/group/project (in case you need for a specific subject)"
    echo "  -w, --work            Set the path for working directory (default: ${main_dir})"
    echo "  -c, --config          Set the path for configurtion file (required)"
    echo "  -pf, --python_file    Set the path for python file in case you run dcm2bids from source code. Like path_to_dcm2bids/dcm2bids.py"
    echo "  -ch, --check          Check on which project under given group you have access. Use -ch -g group_name"
    echo "  -dbo, --dcm2bids_opt  Put any command line arguments you need to add for dcm2bids, like \"--auto_extract_entities --force_dcm2bids --clobber\" etc. Put all inside one quotation"

    echo "  -h, --help            Show this help message"
    exit 1
}

check_access() {
    if [[ -z $1 ]]; then
      echo "You should specify the group's name. Please use -ch -g group_name to proceed"
      exit 1;
    fi
    group="$1"
    echo "################################"
    echo "You have access to the following projects under ${group} group";

    fw ls "fw://${group}"

    echo "################################"
    exit 1
}
# Parse the arguments as key-value pairs
while [[ $# -gt 0 ]]; do
    case "$1" in
        -g|--group) group="$2"; shift 2 ;;
        -p|--project) project="$2"; shift 2 ;;
        -s|--subject) subject_id="$2"; shift 2 ;;
        -w|--work) main_dir="$2"; shift 2 ;;
        -c|--config) config_file="$2"; shift 2 ;;
        -pf|--python_file) bids_py="$2"; shift 2 ;;
        -ch|--check) check_access "$3"; shift 2 ;;
        -dbo|--dcm2bids_opt) dcm2bids_option="$2"; shift 2 ;;

        -h|--help) show_help; exit ;;
        *) echo "Invalid option: $2";  show_help;  exit 1 ;;
    esac
done

if [[ -z $group || -z $project || -z $config_file ]]
then
  echo "################################"
  echo "ERROR: -g group_on_flywheeil -p project_under_group_on_flywheel -c config_file are required arguments. Use -h option to see the usage!";
  echo "################################"
  exit 1;
fi

if [[ ${main_dir} == '.' || ${main_dir} == './' || ${main_dir} == './.' ]]
  then
    main_dir="${PWD}"
fi

work_dir="${main_dir}/${group}/${project}/work"
dicom_dir="${main_dir}/${group}/${project}/dicom_rawdata"
bids_dir="${main_dir}/${group}/${project}/bids"

echo "creating  ${work_dir}"
mkdir -p ${work_dir}
echo "creating  ${dicom_dir}"
mkdir -p ${dicom_dir}
echo "creating  ${bids_dir}"
mkdir -p ${bids_dir}

rm -rf "${work_dir}"/*.*
rm -rf "${dicom_dir}"/*

proj_path="fw://"${group}/${project}/${subject_id}
echo "You asked for the "$proj_path "to be downloaded"

if [[ -z $subject_id ]]; then
      #LS="$(fw ls ${proj_path} -y -a)"
      list_file=${work_dir}/${group}'_'${project}'_subjects.txt'
      fw ls ${proj_path} -y -a > ${list_file}

      # Check if the input file exists
      if [ ! -f "$list_file" ]; then
          echo "Input file containing the list of subjects is not found: $list_file"
          exit 1
      fi

      cd ${work_dir}

      # Read each line from the input file
      while IFS= read -r line; do
          # Check if the line contains the word "Subject"
          if [[ "$line" == *"Subject"* ]]; then
              # Extract "Subject" and everything after it
              sub=$(echo "$line" | sed 's/.*\(Subject.*\)/\1/; s/[[:space:]]*$//')
              echo "download command is: fw download ${proj_path}/$sub -y -i dicom -i bvec -i bval"
              fw download ${proj_path}/"${sub}" -y -i dicom -i bvec -i bval
              echo "Subject $sub was downloaded"
              echo "Now unzipping the zipped dicom files ..."
              tar -zxf "$sub".tar -C .
              mv "scitran"/${group}/${project}/"${sub}" ${dicom_dir}/.
          fi
      done < "$list_file"

elif [[ $subject_id ]]; then
  echo "download command is: fw download ${proj_path} -y -i dicom -i bvec -i bval"
  fw download ${proj_path} -y -i dicom -i bvec -i bval
  echo "Subject $subject_id was downloaded"
  echo "Now unzipping the zipped dicom files ..."
  tar -zxf "$subject_id".tar -C .
  mv "scitran"/${group}/${project}/"${subject_id}" ${dicom_dir}/.

fi

rm -rf "${work_dir}"/scitran

find ${dicom_dir} -name '*.zip' -exec sh -c 'unzip -j -d "`dirname \"{}\"`" "{}"' ';' ; find ${dicom_dir} -name '*.zip' -exec sh -c 'rm "{}"' ';'

find ${dicom_dir} -type d -name "fw__*" -execdir mv {} ses_01 \;


if [ "${bids_py}" ]; then
    run_command="python3 ${bids_py}"
else
    run_command="dcm2bids"
fi

# Check if the dicom_dir exists
if [ -d "$dicom_dir" ]; then
    # Loop through each subject
    for subject in "$dicom_dir"/*; do
        if [ -d "$subject" ]; then
            # Extract subject_ids from subject name using parameter expansion
            subject_id="${subject##*[!0-9]}"

            # Check if extraction was successful
            if [ "$subject_id" != "$subject" ]; then
                echo "Found subject: $subject"
                # echo "Extracted subject_id: $subject_id"

                # Perform dcm2bids with the extracted subject_id
                echo "Running the comamnd $run_command -d $subject -o $bids_dir -p $subject_id -s 01 -c $config_file $dcm2bids_option"
                $run_command -d $subject -o $bids_dir -p $subject_id -s 01 -c $config_file $dcm2bids_option

                echo "dcm2bids done for the subject_id: $subject_id"
            fi
        fi
    done
else
    echo "dicom_dir not found: $dicom_dir"
fi

find $bids_dir -name '*sbref.bval' -exec sh -c 'rm "{}"' ';' ; find $bids_dir -name '*sbref.bvec' -exec sh -c 'rm "{}"' ';'