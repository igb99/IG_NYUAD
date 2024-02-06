#!/bin/bash
#

# initialize variables
# PROJECTNAME='mriqc'
PROJECTBASE=${PWD}
# PROJECTROOT=${PROJECTBASE}/${PROJECTNAME}
# DATA=${PROJECTROOT}"/data"
OUTDIR="out"
WORKDIR="work"
FSL_LICENSE=${FREESURFER_HOME}/license.txt


### Get the user defined parameters ###
# usage function
function usage()
{
   cat << HEREDOC


    usage: cbh_core.sh -d PATH_TO_INPUT_DATA -p ANALYSIS_PIPELINE [-o outdir] [-w workdir] [-r projectroot] [-fl fs-license-file]
    arguments:
     [-h  | --help]                     show this help message and exit
     [-d  | --data]             PATH    path to the root of BIDS input data
     [-o  | --outdir]           PATH    the directory where the results are saved
     [-w  | --workdir]          PATH    the directory where the temporary results are saved
     [-p  | --projectname]      STR     one of the analysis tool like mriqc, aslprep, qsiprep, fmriprep
     [-r  | --projectroot]      PATH    the root path to store all data for different projects
     [-fl | --fs-license-file]  FILE    path/file to the fsl license

HEREDOC
}

while [[ $# -gt 0 ]]; do
# while true; do
  case $1 in
    -h|--help) usage; exit; ;;
    -d|--data) DATA="$2"; shift 2 ;;
    -o|--outdir) OUTDIR="$2"; shift 2 ;;
    -w|--workdir) WORKDIR="$2"; shift 2 ;;
    -r|--projectroot) PROJECTBASE="$2"; shift 2 ;;
    -p|--projectname) PROJECTNAME="$2"; shift 2 ;;
    -fl|--fs-license-file) FSL_LICENSE="$2"; shift 2 ;;
    -*|--*) echo "Unknown option $1"; exit 1 ;;
  esac
done

if [[ -z $DATA || -z $PROJECTNAME ]]
then
  echo "ERROR: -d PATH_TO_INPUT_DATA -p ANALYSIS_PIPELINE are required arguments. See usage: cbh_core.sh -h";
  exit 1;
fi

if [[ ${PROJECTBASE} == '.' || ${PROJECTBASE} == './' || ${PROJECTBASE} == './.' ]]
  then
    PROJECTBASE=${PWD}
fi

if [[ ${DATA} == '.' || ${DATA} == './' || ${DATA} == './.' ]]
  then
    DATA=${PWD}
fi


PROJECTROOT=${PROJECTBASE}/${PROJECTNAME}
# DATA=${PROJECTROOT}/${DATA}
input_bids_dir=${DATA}
OUTDIR=${PROJECTROOT}/${OUTDIR}
WORKDIR=${PROJECTROOT}/${WORKDIR}
FSL_LICENSE=${FSL_LICENSE}


if [[ -d ${PROJECTROOT} ]]
then
    echo ${PROJECTROOT} already exists
    # exit 1
fi

if [[ ! -w $(dirname ${PROJECTROOT}) ]]
then
    echo Unable to write to ${PROJECTROOT}\'s parent. Change permissions and retry
    # exit 1
fi

# echo project name: $'\t\t' ${PROJECTNAME}
# echo project root: $'\t\t' ${PROJECTROOT}
# echo input data path: $'\t' ${DATA}
# echo output directory: $'\t' ${OUTDIR}
# echo working directory: $'\t' ${WORKDIR}
# echo fsl license file: $'\t' ${FSL_LICENSE}
#


# We create a folder named mriqc as well as conda environment with the same name

# module load anaconda3/2020.07
module load miniconda/3-4.11.0
module load singularity/3.8.3

conda_env_path=$SCRATCH/"conda-envs"
singularity_tmp=$SCRATCH/"singularity_temp_folder"
mkdir -p $conda_env_path/pkgs
mkdir -p $singularity_tmp

# Set the conda env path in scratch to reduce the file size in HOME directory
grep -qxF "export CONDA_ENVS_PATH=$conda_env_path" ~/.bashrc || echo "export CONDA_ENVS_PATH=$conda_env_path" >> ~/.bashrc
grep -qxF "export CONDA_PKGS_DIRS=$conda_env_path/pkgs" ~/.bashrc || echo "export CONDA_PKGS_DIRS=$conda_env_path/pkgs" >> ~/.bashrc

# Set the tempdata directory for the singularity to be in scratch
grep -qxF "export SINGULARITY_CACHEDIR=$singularity_tmp" ~/.bashrc || echo "export SINGULARITY_CACHEDIR=$singularity_tmp" >> ~/.bashrc
grep -qxF "export SINGULARITY_TMPDIR=$singularity_tmp" ~/.bashrc || echo "export SINGULARITY_TMPDIR=$singularity_tmp" >> ~/.bashrc
grep -qxF "export SINGULARITY_BINDPATH=$singularity_tmp" ~/.bashrc || echo "export SINGULARITY_BINDPATH=$singularity_tmp" >> ~/.bashrc

source ~/.bashrc


ENV=${PROJECTNAME}
env_path=${PROJECTROOT}

mkdir -p $env_path
cd $env_path

## Set your input directory where it contains BIDS formated data. In that directory you should have the folders for each subject separately starting with sub-*** and having dataset_description.json file available
# input_bids_dir="/scratch/ig2383/HCPAging_BIDS_50"

## We make a list out of all BIDS available data. The plan is to make a job array. The list can be modified or created separately.
list_file=${PROJECTNAME}"_bids_list.txt"
ls -d $input_bids_dir/sub-* | xargs -n1 basename  > $list_file
# ls -d $input_bids_dir/sub-*/ > $list_file

if [ -s $list_file ]; then
    echo "The following subjects will be analysed"
    cat $list_file
else
    echo "File is empty"
    exit 1
fi

source /share/apps/NYUAD5/miniconda/3-4.11.0/etc/profile.d/conda.sh
# source /share/apps/anaconda3/2020.07/etc/profile.d/conda.sh
conda init bash

if conda env list | grep $ENV >/dev/null 2>&1; then
    conda activate $ENV
else
    echo "Creating $ENV environment"
    conda create -n $ENV
    conda activate $ENV
fi

# sif_dir="/share/apps/cbi/singularity/nipreps"
sif_dir=$SCRATCH/"SIF"
ENV_sif_file=$ENV"_latest.sif"
sif_file=$sif_dir/$ENV_sif_file

if [ -f "$sif_file" ]; then
    echo "The container exists"
    rsync -avh -L $sif_file $env_path/$ENV_sif_file
else
    echo "The specified container ($ENV_sif_file) does not exist. The process stops now ..."
    exit 1
fi

out=$env_path/out
work=$env_path/work
logpath=$env_path/logs
license_file=$env_path/fs_license.txt

cat<<EOF>$license_file
rokers@gmail.com
15691
 *CUr0ut.pXO4I
 FS/fjdNnnvKAY
EOF

mkdir -p $logpath

if [ "$ENV" = "mriqc" ]; then
    while read -r line
    do
       echo "Starting the analysis for the subject $line"
       sbatch -o $logpath/job.%J.out -e $logpath/job.%J.err -t 24:00:00 -p compute -N 1 -c 8 \
       --wrap "singularity run --cleanenv $ENV_sif_file \
                  $input_bids_dir \
                  $out \
                  participant \
                  --participant-label $line \
                  -w $work"
    done < "$list_file"
elif [ "$ENV" = "fmriprep" ]; then
    while read -r line
    do
       echo "Starting the analysis for the subject $line"
       sbatch -o $logpath/job.%J.out -e $logpath/job.%J.err -t 24:00:00 -p compute -N 1 -c 8 \
       --wrap "singularity run --cleanenv $ENV_sif_file \
                 $input_bids_dir \
                 $out \
                 participant \
                 --participant-label $line \
                 -w $work \
                 --fs-license-file $license_file \
                 --skip_bids_validation"
    done < "$list_file"
elif [ "$ENV" = "qsiprep" ]; then
    while read -r line
    do
      echo "Starting the analysis for the subject $line"
      sbatch -o $logpath/job.%J.out -e $logpath/job.%J.err -t 24:00:00 -p compute -N 1 -c 8 \
      --wrap "singularity run --cleanenv $ENV_sif_file \
                $input_bids_dir \
                $out \
                participant \
                --participant-label $line\
                -w $work \
                --fs-license-file $license_file \
                --skip_bids_validation \
                --output-resolution 1.2"
    done < "$list_file"
elif [ "$ENV" = "aslprep" ]; then
    while read -r line
    do
       echo "Starting the analysis for the subject $line"
       sbatch -o $logpath/job.%J.out -e $logpath/job.%J.err -t 24:00:00 -p compute -N 1 -c 8 \
       --wrap "singularity run --cleanenv $ENV_sif_file \
                 $input_bids_dir \
                 $out \
                 participant \
                 --participant-label $line \
                 -w $work \
                 --fs-license-file $license_file \
                 --skip_bids_validation"
    done < "$list_file"
else
  echo "None of MRIQC, fMRIPrep or qsiprep started to run. Please check your input!"
fi
