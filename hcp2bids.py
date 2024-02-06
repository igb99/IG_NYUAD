import argparse
import os, glob, shutil
import re, json, numpy
import sys
import nibabel as ni


def dif2dwi(subjects):
    if not os.path.exists(os.path.join(subjects, 'unprocessed/Diffusion')):
        print ("Diffusion directory does not exist")
        return

    dwi = os.path.join(bids, 'dwi/')
    if not os.path.exists(dwi):
        os.mkdir(dwi)
    print(dwi)

    subj_raw = os.path.join(subjects, 'unprocessed/')
    dif_list = glob.glob(os.path.join(subj_raw, 'Diffusion/*dMRI*'))
    dmri_txt = subjects.split('/')[-1] + '_dMRI'

    rr = os.path.join(dwi.replace('dwi/', ''), 'sub-' + sub + '_conversion_list.json')
    jsonFile = open(rr, 'r+')
    data = json.load(jsonFile)

    for dwi_data in dif_list:
        r_1 = os.path.split(dwi_data)[1].replace(dmri_txt + '_', 'acq-')

        if 'SBRef' in r_1:
            r_2 = re.sub('_', '', r_1, 1).lower()
        else:
            r_2 = re.sub('_', '', r_1, 1).lower().replace('.', '_dwi.', 1)

        dst = dwi + 'sub-' + sub + '_' + r_2
        print(dst)
        shutil.copy(dwi_data, dst)

        source = dwi_data.split('/')[-4]+'/'+dwi_data.split('/')[-3]+'/'+dwi_data.split('/')[-2]+'/'+dwi_data.split('/')[-1]
        converted = 'sub-' + sub + '/' + 'dwi/' + 'sub-' + sub + '_' + r_2
        if source not in data:
            data[source] = converted
        jsonFile.seek(0)
    json.dump(data, jsonFile, indent=2)
    jsonFile.close()


def tw2anat(subjects):
    anat = os.path.join(bids, 'anat/')
    if not os.path.exists(anat):
        os.mkdir(anat)
    print(anat)

    subj_raw = os.path.join(subjects, 'unprocessed/')
    tw_list = glob.glob(os.path.join(subj_raw, 'T?w*/*.nii.gz'))
    conv_list = os.path.join(anat.replace('anat/', ''), 'sub-' + sub + '_conversion_list.json')
    jsonFile = open(conv_list, 'r+')
    data = json.load(jsonFile)

    run = 1
    for tw_data in tw_list:
        base_file_name = tw_data.split('/')[-1].split('.')[0]
        modality = tw_data.split('/')[-1].split('_')[3]
        tail = tw_data.split('/')[-1][-7:]

        filename = 'sub-' + sub + '_' + 'run-' + '{:02d}'.format(run) + '_' + modality
        dst = anat + filename + tail
        dst_json = anat + filename + '.json'

        print(dst)
        shutil.copy(tw_data, dst)
        shutil.copy(tw_data.split('.')[0] + '.json', dst_json)
        run = run + 1

        source = tw_data.split('/')[-4] + '/' + tw_data.split('/')[-3] + '/' + tw_data.split('/')[-2] + '/' + tw_data.split('/')[-1]
        converted = 'sub-' + sub + '/' + 'anat/' + filename + tail
        if source not in data:
            data[source] = converted

        source_json = tw_data.split('/')[-4] + '/' + tw_data.split('/')[-3] + '/' + tw_data.split('/')[-2] + '/' + base_file_name + '.json'
        converted_json = 'sub-' + sub + '/' + 'anat/' + filename + '.json'
        if source_json not in data:
            data[source_json] = converted_json

        jsonFile.seek(0)
    json.dump(data, jsonFile, indent=2)
    jsonFile.close()


def fmri2func(subjects):
    func = os.path.join(bids, 'func/')
    if not os.path.exists(func):
        os.mkdir(func)
    print(func)

    subj_raw = os.path.join(subjects, 'unprocessed/')
    task_list = glob.glob(os.path.join(subj_raw, '*fMRI*/*fMRI_*'))
    conv_list = os.path.join(func.replace('func/', ''), 'sub-' + sub + '_conversion_list.json')
    jsonFile = open(conv_list, 'r+')
    data = json.load(jsonFile)

    for task_data in task_list:
        filename_split = task_data.split('/')
        task1 = filename_split[-2].split('_')[1]
        task = ''.join([i for i in task1 if not i.isdigit()])
        acq = filename_split[-2].split('_')[2]

        tail = filename_split[-1][-7:]
        if 'json' in tail:
            tail = filename_split[-1][-5:]

        if 'SBRef' in filename_split[-1]:
            ref = 'sbref'
        else:
            ref = "bold"

        if task == 'REST':
            run = int("".join(filter(str.isdigit, task1)))
            # print(run)
            filename = 'sub-' + sub + '_task-' + task + '_acq-' + acq + '_run-' + '{:02d}'.format(run) + '_' + ref + tail
        else:
            filename = 'sub-' + sub + '_task-' + task + '_acq-' + acq + '_' + ref + tail

        dst = func + filename
        print(dst)
        shutil.copy(task_data, dst)

        if tail.split('.')[-1] == 'json':
            with open(dst) as jsf:
                json_decoded = json.load(jsf)

            json_decoded['TaskName'] = task

            with open(dst, 'w') as jsf:
                json.dump(json_decoded, jsf, indent=4)

        source = task_data.split('/')[-4] + '/' + task_data.split('/')[-3] + '/' + task_data.split('/')[-2] + '/' + \
                 task_data.split('/')[-1]

        converted = 'sub-' + sub + '/' + 'func/' + filename
        if source not in data:
            data[source] = converted
        jsonFile.seek(0)
    json.dump(data, jsonFile, indent=2)
    jsonFile.close()


def fieldmap2fmap(subjects):
    global fmap
    fmap = os.path.join(bids, 'fmap/')
    if not os.path.exists(fmap):
        os.mkdir(fmap)
    print(fmap)

    subj_raw = os.path.join(subjects, 'unprocessed/')
    fmap_list = glob.glob(os.path.join(subj_raw, '*fMRI*/*SpinEchoFieldMap*.nii.gz'))
    sub_org = subjects.split('/')[-1]

    fmap_filelist_json_dict = {}

    for task_data in fmap_list:
        task_dir = task_data.split('/')[-2]
        '''The acquisition are the last part of the fMRI directories as either Ap or PA'''
        acq = task_dir.split('_')[-1]

        '''We are interested just on .nii.gz file. We can skip the .json files'''
        # if '_'+acq+'.nii.gz' not in task_data:
        if '_' + acq + '.nii.gz' in task_data:
            continue
        # print(task_data)

        '''Get the filename pattern for the functional MRI files'''
        file_init = sub_org + '_' + task_dir
        '''The full path for the current files being processed'''
        current_path = os.path.dirname(task_data)
        '''The path of the current file excluding the initial path of the input directory. This path is common for all HCP data regardless of the location.'''
        main_dir = os.path.join(sub_org, 'unprocessed/',  task_dir)

        '''Get the task name, both the REST with run number and the other without run.'''
        task1 = task_dir.split('_')[-2]
        task = ''.join([i for i in task1 if not i.isdigit()])
        '''We extract the run number from task REST.'''
        if task == 'REST':
            run = int("".join(filter(str.isdigit, task1)))
        '''Set the names for the functional MRI, both BOLD and SBREF files. We need them to find out the converted files under func directory.'''
        file_bold = os.path.join(main_dir, file_init + '.nii.gz')
        file_sbref = os.path.join(main_dir, file_init + '_SBRef.nii.gz')

        '''Open the tracking json file to get the converted files of bold and sbref under func directory.'''
        jsonFile = open(conv_filelist_file, 'r')
        data = json.load(jsonFile)

        '''Creating a json file to save the fmap file and its associated func files.'''
        filename_split = task_data.split('/')[-1]
        data[file_bold] = data[file_bold].replace('sub-' + sub + '/', '', 1)
        data[file_sbref] = data[file_sbref].replace('sub-' + sub + '/', '', 1)

        if filename_split not in fmap_filelist_json_dict:
            fmap_filelist_json_dict[filename_split] = [data[file_bold], data[file_sbref]]

        elif type(fmap_filelist_json_dict[filename_split]) == list:
            fmap_filelist_json_dict[filename_split].append(data[file_bold])
            fmap_filelist_json_dict[filename_split].append(data[file_sbref])

        with open(os.path.join(output_dir, 'sub-'+sub, 'fmap_file_list.json'), 'w') as editfile:
            json.dump(fmap_filelist_json_dict, editfile, indent=4)
        jsonFile.close()

    for key in fmap_filelist_json_dict.keys():
        try:
            run = int("".join(filter(str.isdigit, key.split('_')[-2])))
        except:
            run = 0
        dir = key.split('.')[0][-2:]

        fmapfilename = 'sub-' + sub + '_dir-' + dir + '_run-' + str(run) + '_epi.nii.gz'
        # init_fmapfilename = glob.glob(os.path.join(subj_raw, '*fMRI*'+'_'+dir+'/'+key))[0]
        init_fmapfilename = glob.glob(os.path.join(subj_raw, '*fMRI*'+'/'+key))[0]
        shutil.copy(init_fmapfilename, fmap + fmapfilename)

        jsonfile_org = glob.glob(os.path.join(subj_raw, '*fMRI*/'+key))[0].split('.')[0]+'.json'
        jsonfile_converted = fmapfilename.split('.')[0]+'.json'
        fmapjsonfile = fmap+jsonfile_converted
        shutil.copy(jsonfile_org, fmapjsonfile)

        with open(fmapjsonfile) as jsf:
            json_decoded = json.load(jsf)

        json_decoded['IntendedFor'] = fmap_filelist_json_dict[key]

        with open(fmapjsonfile, 'w') as jsf:
            json.dump(json_decoded, jsf, indent=4)

        '''Add the source and converted file names to the conversion file list'''
        source_nii = jsonfile_org.split('/')[-4] + '/' + jsonfile_org.split('/')[-3] + '/' + jsonfile_org.split('/')[-2] + '/' + jsonfile_org.split('/')[-1]
        source_json = jsonfile_org.split('/')[-4] + '/' + jsonfile_org.split('/')[-3] + '/' + jsonfile_org.split('/')[
            -2] + '/' + key

        with open(conv_filelist_file) as cfl:
            data1 = json.load(cfl)
        if source_nii not in data1:
            data1[source_nii] = 'sub-' + sub + '/fmap/' + fmapjsonfile.split('/')[-1]
        if source_json not in data1:
            data1[source_json] = 'sub-' + sub + '/fmap/' + fmapfilename
        with open(conv_filelist_file, 'w') as cfl:
            json.dump(data1, cfl, indent=4)

    os.remove(os.path.join(output_dir, 'sub-' + sub, 'fmap_file_list.json'))
    print('done with fmap')


def pcasl2perf(subjects):
    if not os.path.exists(os.path.join(subjects, 'unprocessed/mbPCASLhr')):
        print ("mbPCASLhr directory does not exist")
        return

    perf = os.path.join(bids, 'perf/')
    if not os.path.exists(perf):
        os.mkdir(perf)
    print(perf)

    subj_raw = os.path.join(subjects, 'unprocessed/')
    asl_file = glob.glob(os.path.join(subj_raw, 'mbPCASLhr/*mbPCASLhr*.nii.gz'))
    acq = asl_file[0].split('.')[0][-2:]
    asl_file_org = asl_file[0]
    asl_file_json = asl_file[0].split('.')[0] + '.json'
    dst_nii = perf + 'sub-' + sub + '_acq-' + acq + '_asl.nii.gz'
    dst_json = perf + 'sub-' + sub + '_acq-' + acq + '_asl.json'
    dst_tsv = perf + 'sub-' + sub + '_acq-' + acq + '_aslcontext.tsv'

    shutil.copy(asl_file_org, dst_nii)
    shutil.copy(asl_file_json, dst_json)

    f = open(dst_tsv, 'w')
    f.write('volume_type\n')
    for i in range(43):
        f.write('label\ncontrol\n')
    f.write('cbf\ncbf\nm0scan\nm0scan')
    f.close()

    with open(dst_json) as jsf:
        json_decoded = json.load(jsf)

    json_decoded['TotalAcquiredPairs'] =  45
    json_decoded['ArterialSpinLabelingType'] =  'PCASL'

    '''Post-Labeling delays'''
    time_delays = [0.2, 0.7, 1.2, 1.7, 2.2, 0]
    '''Number of acquired volumes at Post-Labeling delays'''
    times_acquired = [12, 12, 12, 20, 30, 4]
    t_arr = []
    for i in range(len(times_acquired)):
        t_arr1 = [time_delays[i]] * times_acquired[i]
        t_arr.extend(t_arr1)

    json_decoded['PostLabelingDelay'] = t_arr
    json_decoded['BackgroundSuppression'] = False
    json_decoded['M0Type'] = 'Included'
    json_decoded['RepetitionTimePreparation'] = 3.71
    json_decoded['LabelingDuration'] = 1.5

    with open(dst_json, 'w') as jsf:
        json.dump(json_decoded, jsf, indent=4)

    fmap_file_nii = glob.glob(os.path.join(subj_raw, 'mbPCASLhr/*PCASLhr_SpinEchoFieldMap_' + acq + '.nii.gz'))[0]
    fmap_file_json = glob.glob(os.path.join(subj_raw, 'mbPCASLhr/*PCASLhr_SpinEchoFieldMap_' + acq + '.json'))[0]

    dst_fmap_file_nii = fmap + 'sub-' + sub + '_dir-' + acq + '_run-0' + '_epi.nii.gz'
    dst_fmap_file_json = fmap + 'sub-' + sub + '_dir-' + acq + '_run-0' + '_epi.json'

    shutil.copy(fmap_file_nii, dst_fmap_file_nii)
    shutil.copy(fmap_file_json, dst_fmap_file_json)

    with open(dst_fmap_file_json) as jsf1:
        json_decoded1 = json.load(jsf1)

    json_decoded1['IntendedFor'] = 'perf/' + 'sub-' + sub + '_acq-' + acq + '_asl.nii.gz'

    with open(dst_fmap_file_json, 'w') as jsf1:
        json.dump(json_decoded1, jsf1, indent=4)

    '''Updating the conversion file list'''
    source_fmap_nii = asl_file_org.split('/')[-4] + '/' + 'unprocessed/mbPCASLhr/' + fmap_file_nii.split('/')[-1]
    source_fmap_json = asl_file_json.split('/')[-4] + '/' + 'unprocessed/mbPCASLhr/' + fmap_file_json.split('/')[-1]

    source_nii = asl_file_org.split('/')[-4] + '/' + 'unprocessed/mbPCASLhr/' + asl_file_org.split('/')[-1]
    source_json = asl_file_json.split('/')[-4] + '/' + 'unprocessed/mbPCASLhr/' + asl_file_json.split('/')[-1]

    with open(conv_filelist_file) as cfl:
        data1 = json.load(cfl)

    if source_fmap_nii not in data1:
        data1[source_fmap_nii] = 'sub-' + sub + '/fmap/' + dst_fmap_file_nii.split('/')[-1]
    if source_fmap_json not in data1:
        data1[source_fmap_json] = 'sub-' + sub + '/fmap/' + dst_fmap_file_json.split('/')[-1]

    if source_nii not in data1:
        data1[source_nii] = 'sub-' + sub + '/perf/' + dst_nii.split('/')[-1]
    if source_json not in data1:
        data1[source_json] = 'sub-' + sub + '/perf/' + dst_json.split('/')[-1]

    with open(conv_filelist_file, 'w') as cfl:
        json.dump(data1, cfl, indent=4)


def hcp2bids():
    import os
    global input_dir, output_dir
    global bids, func, fmap, anat, dwi, perf, beh, sub
    global conv_filelist_file, bidsignore_file

    input_dir = os.path.abspath(input_dir)
    output_dir = os.path.abspath(output_dir)

    '''Create the .bidsignore file. In this file we should list the name of additional files created during conversion that should be ignored by bids validator.'''
    bidsignore_file = os.path.join(output_dir, '.bidsignore')
    bidsignore = open(bidsignore_file, 'w')

    # get hcp subject directory paths
    sub_dir = [os.path.join(input_dir, o) for o in os.listdir(input_dir) if os.path.isdir(os.path.join(input_dir, o))]

    for i, subjects in enumerate(sub_dir):
        # if i < 4 or i > 4:
        # if i <= 105:
        #     continue
        subj_raw = os.path.join(subjects, 'unprocessed/')
        print(subj_raw)

        # output directory for the subject
        # bids = os.path.join(output_dir, subjects.split('/')[-1])
        if subjects.split('/')[-1] == "":
            sub_org = subjects.split('/')[-2]
            sub = subjects.split('/')[-2].replace('_', '').lower()
        else:
            sub_org = subjects.split('/')[-1]
            sub = subjects.split('/')[-1].replace('_', '').lower()

        bids = os.path.join(output_dir.replace(sub_org + '/', ''), 'sub-' + sub + '/')
        print(bids)
        if not os.path.exists(bids):
            os.mkdir(bids)

        # output directory paths for fmap, func, anat and dwi
        # beh = os.path.join(bids, 'beh/')
        # if not os.path.exists(beh):
        #     os.mkdir(beh)
        # print(beh)

        conv_filelist_json_dict = {}
        conv_filelist_file = os.path.join(bids, 'sub-'+sub+'_conversion_list.json')
        with open(conv_filelist_file, 'w') as editfile:
            json.dump(conv_filelist_json_dict, editfile, indent=4)

        bidsignore.write('sub-' + sub + '/sub-'+sub+'_conversion_list.json' + '\n')
        # list_all_files = glob.glob(os.path.join(subj_raw, '**'), recursive=True)
        # print(os.path.isdir(list_dir[0]))

        dif2dwi(subjects)
        print("done with Diffusion to DWI's for --", subjects)

        tw2anat(subjects)
        print("done with T1w and T2w to anat for --", subjects)

        fmri2func(subjects)
        print("done with fmri to func for --", subjects)

        fieldmap2fmap(subjects)
        print("done with fieldmap to fmap for --", subjects)

        pcasl2perf(subjects)
        print("done with mbPCASL to perf for --", subjects)

        driv_dir = os.path.join(output_dir, 'derivatives')
        if not os.path.exists(driv_dir):
            os.mkdir(driv_dir)

        #shutil.move(os.path.join(output_dir, conv_filelist_file), os.path.join(driv_dir, conv_filelist_file))
        shutil.move(conv_filelist_file, driv_dir+'/'+'sub-'+sub+'_conversion_list.json')

    bidsignore.close()
    print(bidsignore_file)


def dataset_readme(output_dir):

    dset_desc_json_dict = {}
    dset_desc_json_dict["Name"] = "Human Connectome Project (HCP) Development & Aging data in BIDS format"
    dset_desc_json_dict["BIDSVersion"] = "1.8.0"
    dset_desc_json_dict["Authors"] = ["Iraj Gholami @ NYUAD", "Rokers Lab at NYUAD"]

    with open(os.path.join(output_dir, 'dataset_description.json'), 'w') as editfile:
        json.dump(dset_desc_json_dict, editfile, indent=4)

    f = open(os.path.join(output_dir, 'README'), 'w+')
    f.write('Converted from HCPD Nifty file to BIDS structure. \n')
    f.write('All HCP data were downloaded from ConnectomeDB. These data are already converted from DICOM to NIFTI, but the file naming and folder structure are not as specified for BIDS.\n')
    f.write('The current folder contains the converted HCPD NIFTI data to the BIDS structure.\n')
    f.close()


def main():
    import argparse
    import sys

    class MyParser(argparse.ArgumentParser):
        def error(self, message):
            sys.stderr.write('error: %s\n' % message)
            self.print_help()
            sys.exit(2)

    parser = MyParser(
        description="HCP to BIDS converter.",
        fromfile_prefix_chars='@'
    )

    parser.add_argument(
        "input_dir",
        help="Location of the root of your HCP dataset directory",
        metavar="input_dir"
    )
    parser.add_argument(
        "output_dir",
        help="Directory where BIDS data will be stored",
        metavar="output_dir"
    )

    args = parser.parse_args()

    '''Define global variables'''
    global conv_filelist_file, bidsignore_file
    global input_dir, output_dir
    global bids, func, fmap, anat, dwi, perf, beh

    input_dir = vars(args)['input_dir']
    output_dir = vars(args)['output_dir']
    if output_dir == '.' or output_dir == './':
        output_dir = os.getcwd()

    print("Input Directory: ", input_dir)
    print("Output Directory: ", output_dir)

    dataset_readme(output_dir)
    print('\nThe dataset_description.json and README were created')

    print("\nRunning hcp2bids")
    # hcp2bids(input_dir, output_dir)
    hcp2bids()
    print("\nDone with hcp2bids")


if __name__ == '__main__':
    main()
