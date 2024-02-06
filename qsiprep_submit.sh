#!/bin/bash

module load miniconda
module load singularity

conda_env_path=$SCRATCH/"conda-envs"
singularity_tmp=$SCRATCH/"singularity_temp_folder"
mkdir -p $conda_env_path/pkgs
mkdir -p $singularity_tmp

## Set the conda env path in scratch to reduce the file size in HOME directory
grep -qxF "export CONDA_ENVS_PATH=$conda_env_path" ~/.bashrc || echo "export CONDA_ENVS_PATH=$conda_env_path" >> ~/.bashrc
grep -qxF "export CONDA_PKGS_DIRS=$conda_env_path/pkgs" ~/.bashrc || echo "export CONDA_PKGS_DIRS=$conda_env_path/pkgs" >> ~/.bashrc

## Set the tempdata directory for the singularity to be in scratch
grep -qxF "export SINGULARITY_CACHEDIR=$singularity_tmp" ~/.bashrc || echo "export SINGULARITY_CACHEDIR=$singularity_tmp" >> ~/.bashrc
grep -qxF "export SINGULARITY_TMPDIR=$singularity_tmp" ~/.bashrc || echo "export SINGULARITY_TMPDIR=$singularity_tmp" >> ~/.bashrc
grep -qxF "export SINGULARITY_BINDPATH=$singularity_tmp" ~/.bashrc || echo "export SINGULARITY_BINDPATH=$singularity_tmp" >> ~/.bashrc

source ~/.bashrc

## We create a folder named qsiprep as well as conda environment with the same name
ENV="qsiprep"
env_path=$SCRATCH/$ENV
mkdir -p $env_path
cd $env_path

## Set your input directory where it contains BIDS formated data. In that directory you should have the folders for each subject separately starting with sub-*** and having dataset_description.json file available
input_bids_dir=$env_path/"bids_test_data"

## We make a list out of all BIDS available data. The plan is to make a job array. The list can be modified or created separately.
list_file="qsiprep_bids_list.txt"
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
conda init bash

if conda env list | grep $ENV >/dev/null 2>&1; then
    conda activate $ENV
else
    echo "Creating $ENV environment"
    conda create -n $ENV
    conda activate $ENV
fi

sif_file="containers_bids-qsiprep--0.6.6.sif"
if [ -f "$sif_file" ]; then
    echo "The container exists"
else
    echo "Pulling the singularity image ..."
    singularity pull shub://ReproNim/containers:bids-qsiprep--0.6.6
fi

if [ -f "bids-qsiprep-0.6.6.sif" ]; then
    echo ""
else
    cp $sif_file bids-qsiprep-0.6.6.sif
fi

while read -r line
do
  echo "Starting the analysis for the subject $line"
  sbatch -o job.%J.out -e job.%J.err -t 24:00:00 -p compute -N 1 -c 8 \
  --wrap "singularity run --cleanenv bids-qsiprep-0.6.6.sif \
            $input_bids_dir \
            $env_path/output \
            participant \
            --participant-label $line\
            -w $env_path/work \
            --fs-license-file $env_path/license.txt \
            --skip_bids_validation \
            --output-resolution 1.2"
done < "$list_file"

## singularity run --cleanenv bids-qsiprep-0.6.6.sif $SCRATCH/qsiprep/HPCAging_PosteriorCorticalAtrophy/sub-hca6010538v1mr $SCRATCH/qsiprep/output participant -w $SCRATCH/qsiprep/work --fs-license-file $SCRATCH/qsiprep/license.txt --skip_bids_validation --output-resolution 1.2

## conda deactivate
## conda clean -a
## pip cache purge
