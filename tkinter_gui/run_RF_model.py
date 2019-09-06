import pandas as pd
import pickle
from sklearn.preprocessing import MinMaxScaler
import numpy as np
import statistics
import os
from configparser import ConfigParser
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

def rfmodel(inifile):

    config = ConfigParser()
    configFile = str(inifile)
    config.read(configFile)
    csv_dir = config.get('General settings', 'csv_path')
    csv_dir_in = os.path.join(csv_dir, 'features_extracted')
    csv_dir_out = os.path.join(csv_dir, 'machine_results')
    use_master = config.get('General settings', 'use_master_config')
    discrimination_threshold = config.getfloat('RF settings', 'discrimination_threshold')
    if not os.path.exists(csv_dir_out):
        os.makedirs(csv_dir_out)
    model_dir = config.get('SML settings', 'model_dir')
    model_nos = config.getint('SML settings', 'No_targets')
    currentAttackGapList = []
    filesFound = []
    model_paths = []
    target_names = []
    loop = 1
    vNm_list = []
    log_df = pd.DataFrame()
    configFilelist = []
    loopy = 0

    ########### GET MODEL PATHS AND NAMES ###########
    for i in range(model_nos):
        currentModelPaths = 'model_path_' + str(loop)
        currentModelNames = 'target_name_' + str(loop)
        currentModelPaths = config.get('SML settings', currentModelPaths)
        currentModelNames = config.get('SML settings', currentModelNames)
        model_paths.append(currentModelPaths)
        target_names.append(currentModelNames)
        loop += 1
    loop = 0
    target_frames_found = []

    ########### FIND CSV FILES ###########
    if use_master == 'yes':
        for i in os.listdir(csv_dir_in):
            if i.__contains__(".csv"):
                file = os.path.join(csv_dir_in, i)
                filesFound.append(file)
    if use_master == 'no':
        config_folder_path = config.get('General settings', 'config_folder')
        for i in os.listdir(config_folder_path):
            if i.__contains__(".ini"):
                configFilelist.append(os.path.join(config_folder_path, i))
                iniVidName = i.split(".")[0]
                csv_fn = iniVidName + '.csv'
                file = os.path.join(csv_dir_in, csv_fn)
                filesFound.append(file)

    for i in filesFound:
        currFile = i
        if use_master == 'no':
            configFile = configFilelist[loopy]
            config = ConfigParser()
            config.read(configFile)
        loopy += 1
        inputFile = pd.read_csv(currFile, index_col=0)
        inputFileOrganised = inputFile.drop(
            ["Ear_left_1_x", "Ear_left_1_y", "Ear_left_1_p", "Ear_right_1_x", "Ear_right_1_y", "Ear_right_1_p",
             "Nose_1_x", "Nose_1_y", "Nose_1_p", "Center_1_x", "Center_1_y", "Center_1_p", "Lat_left_1_x",
             "Lat_left_1_y",
             "Lat_left_1_p", "Lat_right_1_x", "Lat_right_1_y", "Lat_right_1_p", "Tail_base_1_x", "Tail_base_1_y",
             "Tail_base_1_p", "Tail_end_1_x", "Tail_end_1_y", "Tail_end_1_p", "Ear_left_2_x",
             "Ear_left_2_y", "Ear_left_2_p", "Ear_right_2_x", "Ear_right_2_y", "Ear_right_2_p", "Nose_2_x", "Nose_2_y",
             "Nose_2_p", "Center_2_x", "Center_2_y", "Center_2_p", "Lat_left_2_x", "Lat_left_2_y",
             "Lat_left_2_p", "Lat_right_2_x", "Lat_right_2_y", "Lat_right_2_p", "Tail_base_2_x", "Tail_base_2_y",
             "Tail_base_2_p", "Tail_end_2_x", "Tail_end_2_y", "Tail_end_2_p", ], axis=1)
        video_no = inputFileOrganised.pop('video_no').values
        frame_number = inputFileOrganised.pop('frames').values

        ########## STANDARDIZE DATA ###########################################
        scaler = MinMaxScaler()
        scaled_values = scaler.fit_transform(inputFileOrganised)
        inputFileOrganised.loc[:, :] = scaled_values
        inputFileOrganised['video_no'] = video_no
        videoNames = inputFileOrganised['video_no'].unique()

        for i in videoNames:
            currentVideoName = i
            vNm_list.append('Video' + str(currentVideoName))
            currentDf = (inputFileOrganised.loc[inputFileOrganised['video_no'] == currentVideoName])
            outputDf = (inputFile.loc[inputFile['video_no'] == currentVideoName])
            outputDf.reset_index()
            outputDf['frames'] = outputDf.index

            video_no = currentDf.pop('video_no').values

            for i in range(model_nos):
                currentModelPath = model_paths[i]
                print(currentModelPath)
                model = os.path.join(model_dir, currentModelPath)
                currModelName = os.path.basename(model)
                currModelName = currModelName.split('.')
                currModelName = str(currModelName[0]) + '_prediction'
                currProbName = 'Probability_' + currModelName
                print(currProbName)
                clf = pickle.load(open(model, 'rb'))
                predictions = clf.predict_proba(currentDf)
                outputDf[currProbName] = predictions[:, 1]
                outputDf[currModelName] = np.where(outputDf[currProbName] > discrimination_threshold, 1, 0)

                ########## FIX  'GAPS' ###########################################
                gaps = outputDf[(outputDf[currModelName] == 1) & (outputDf[currModelName].shift(1) == 0) & (
                            outputDf[currModelName].shift(2) == 1)]
                gaps_list = list((gaps['frames']) - 1)
                for index, row in outputDf.iterrows():
                    currentIndex = index
                    if (currentIndex in gaps_list):
                        outputDf.set_value(currentIndex, currModelName, 1)

                ########## FIX  'GAPS' 2 ###########################################
                gaps = outputDf[(outputDf[currModelName] == 0) & (outputDf[currModelName].shift(1) == 1) & (
                            outputDf[currModelName].shift(2) == 0)]
                gaps_list = list((gaps['frames']) - 1)
                for index, row in outputDf.iterrows():
                    currentIndex = index
                    if (currentIndex in gaps_list):
                        outputDf.set_value(currentIndex, currModelName, 0)

                ########## FIX  'GAPS' 3 ###########################################
                gaps = outputDf[(outputDf[currModelName] == 1) & (outputDf[currModelName].shift(1) == 0) & (
                            outputDf[currModelName].shift(2) == 0) & (outputDf[currModelName].shift(3) == 1)]
                gaps_list = list((gaps['frames']) - 1)
                for index, row in outputDf.iterrows():
                    currentIndex = index
                    if (currentIndex in gaps_list):
                        outputDf.set_value(currentIndex, currModelName, 0)

                ########## FIX  'GAPS' 4 ###########################################
                gaps = outputDf[(outputDf[currModelName] == 1) & (outputDf[currModelName].shift(1) == 0) & (
                            outputDf[currModelName].shift(2) == 0) & (outputDf[currModelName].shift(3) == 0) & (
                                            outputDf[currModelName].shift(4) == 1)]
                gaps_list = list((gaps['frames']) - 1)
                for index, row in outputDf.iterrows():
                    currentIndex = index
                    if (currentIndex in gaps_list):
                        outputDf.set_value(currentIndex, currModelName, 0)

                ########## FIX  'GAPS' 5 ###########################################
                gaps = outputDf[(outputDf[currModelName] == 1) & (outputDf[currModelName].shift(1) == 0) & (
                            outputDf[currModelName].shift(2) == 0) & (outputDf[currModelName].shift(3) == 0) & (
                                            outputDf[currModelName].shift(4) == 0) & (
                                            outputDf[currModelName].shift(5) == 1)]
                gaps_list = list((gaps['frames']) - 1)
                for index, row in outputDf.iterrows():
                    currentIndex = index
                    if (currentIndex in gaps_list):
                        outputDf.set_value(currentIndex, currModelName, 0)

                ########## FIX  'GAPS' 5 ###########################################
                gaps = outputDf[(outputDf[currModelName] == 1) & (outputDf[currModelName].shift(1) == 0) & (
                            outputDf[currModelName].shift(2) == 0) & (outputDf[currModelName].shift(3) == 0) & (
                                            outputDf[currModelName].shift(4) == 0) & (
                                            outputDf[currModelName].shift(5) == 0) & (
                                            outputDf[currModelName].shift(6) == 1)]
                gaps_list = list((gaps['frames']) - 1)
                for index, row in outputDf.iterrows():
                    currentIndex = index
                    if (currentIndex in gaps_list):
                        outputDf.set_value(currentIndex, currModelName, 0)

                ########## FIX  'GAPS' 6 ###########################################
                gaps = outputDf[(outputDf[currModelName] == 1) & (outputDf[currModelName].shift(1) == 0) & (
                            outputDf[currModelName].shift(2) == 0) & (outputDf[currModelName].shift(3) == 0) & (
                                            outputDf[currModelName].shift(4) == 0) & (
                                            outputDf[currModelName].shift(5) == 0) & (
                                            outputDf[currModelName].shift(6) == 0) & (
                                            outputDf[currModelName].shift(7) == 1)]
                gaps_list = list((gaps['frames']) - 1)
                for index, row in outputDf.iterrows():
                    currentIndex = index
                    if (currentIndex in gaps_list):
                        outputDf.set_value(currentIndex, currModelName, 0)

            ########## SCORE SEVERITY OF BEHAVIOURS by NOMALIZED MOVEMENT SCORE ###########################################
            mouse1size = (statistics.mean(outputDf['Mouse_1_nose_to_tail']))
            mouse2size = (statistics.mean(outputDf['Mouse_2_nose_to_tail']))
            mouse1Max = mouse1size * 8
            mouse2Max = mouse2size * 8

            outputDf['Scaled_movement_M1'] = (outputDf['Total_movement_all_bodyparts_M1'] / (mouse1Max))
            outputDf['Scaled_movement_M2'] = (outputDf['Total_movement_all_bodyparts_M2'] / (mouse2Max))
            outputDf['Scaled_movement_M1_M2'] = (outputDf['Scaled_movement_M1'] + outputDf['Scaled_movement_M2']) / 2
            outputDf['Scaled_movement_M1_M2'] = outputDf['Scaled_movement_M1_M2'].round(decimals=2)

            outFname = str('Video') + str(int(currentVideoName)) + str('.csv')
            outFname = os.path.join(csv_dir_out, outFname)
            outputDf.to_csv(outFname)
            print(str(outFname) + str(' completed'))