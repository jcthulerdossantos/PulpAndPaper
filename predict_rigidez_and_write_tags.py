#Packages
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import arrow
import pytz
from tzlocal import get_localzone
import pickle

#Não printar mensagens de segurança
import warnings
warnings.filterwarnings("ignore")

#PI Web API Client
import osisoft.pidevclub.piwebapi

#Liberar acesso ao servidor
user= #USER
pw = #PASSWORD
    
from osisoft.pidevclub.piwebapi.pi_web_api_client import PIWebApiClient  
client = PIWebApiClient('https://NAME_DIR/piwebapi', False, user, pw, False) #não dobrar as barras
path = 'pi:\\\\NAME_DIR_LOCAL\\'

#Web IDs das tags de predição de rigidez
def web_ids():
    point1 = client.point.get_by_path('\\\\fliptop21\\B6RIGIDEZ_L_FRC', None)  
    point2 = client.point.get_by_path('\\\\fliptop21\\B6RIGIDEZ_T_FRC', None) 

    webIds = list()  
    webIds.append(point1.web_id)
    webIds.append(point2.web_id)
    
    return webIds

#Descobrir data e hora do último valor das tags de predição
def last_prediction(webIds):

    timestamp_L = client.stream.get_value_with_http_info(webIds[0])[0].timestamp
    timestamp_T = client.stream.get_value_with_http_info(webIds[1])[0].timestamp

    last_value = min(timestamp_L, timestamp_T)
    
    return last_value

#Ler tags necessárias para predição entre últimos valor e 'agora'
def extracting_data(last_value):
    
    list_tags=['B6OPT_ROLO','B6P1XDHD.BRKAC','B6OPT_119_AVG','B6OPT_120_AVG','B6OPT_015_AVG','B6OPT_183_AVG','B6OPT_158_AVG',
               'B6FPGRADE','B6AI0111_M','B6AI0113_M','B6AI0112_M','B6PCTPASTA_HST','B6PCTREF_HST','B6JETOWIRE1PV',
               'B6JETOWIRE4PV','B6JETOWIRE2PV','B6HBXCNDEVPV','B6HBX4CNDEVPV','B6HBX2CNDEVPV','B6FI0571PV','B6CNSCL1_HST',
               'B6CNSCL4_HST','B6CNSCL2_HST','B6AI0004_M','B6AI0006_M','B6DRYNESSL1PV','B6DRYNESSL4PV','B6ESP0001_HST',
               'B6ESP0002_HST','B6ESP0003_HST','B6ESP0005_HST','B6ESP0006_HST','B6ESP0007_HST','B6ESP0008_HST','B6ESP0009_HST',
               'B6ESP0010_HST','B6ESP0015_HST','B6ESP0016_HST','B6PCCL2_HST','B6MFVAT01WFPV','B6AI0405PV','B6MFVAT04WFPV',
               'B6AI0480PV','B6MFVAT02WFPV','B6AI0430PV','B6P1XDHDRESPDAPV','B6CALPI911','B6CASWTPV','B6ESPESPV','B6MOISS1PV']

    paths = []

    for tag in list_tags:
        paths.append(path + tag)

    df = client.data.get_multiple_interpolated_values(paths, start_time = last_value, end_time = '*', interval = '1m')

    #selecionar apenas as colunas de valores e uma coluna de Timestamp
    numbers = np.arange(1,51,1)
    value = 'Value'
    list_values = ['Timestamp1']
    for number in numbers:
        list_values.append(value + str(number))
    df = df.loc[:,list_values]

    #renomear as colunas com nomes das tags
    list_tags.insert(0,'TIMESTAMP')
    df = df.rename(columns = dict(zip(list_values,list_tags)))

    #trocar dados de gramatura, espessura e umidade do lab por dados do scanner (trocar ordem, drop, rename)
    tags_lab = ['B6OPT_015_AVG','B6OPT_183_AVG','B6OPT_158_AVG']
    tags_scanner = ['B6CASWTPV','B6ESPESPV','B6MOISS1PV']

    index_lab = [list(df.columns.values).index(tag) for tag in tags_lab]
    new_list_tags = list(df.columns.values)[:-3]
    for i in range(len(tags_scanner)):
        new_list_tags.insert(index_lab[i],tags_scanner[i])
    df = df[new_list_tags] #trocando ordem! - colocando tags scanner no lugar de tags lab

    df = df.drop(columns = tags_lab) #excluindo tags lab

    df = df.rename(columns = dict(zip(tags_scanner,tags_lab))) #substituindo nome tags scanner por tags lab
    
    return df

#Pré-processamento para predição
def prepare_df(dataframe):
    
    #substituir bad data por NaN
    def fix_bad_data(df, bad_data=["Bad Data","No Data","Bad","I/O Timeout","Calc Failed",
                                   "Arc Off-line","Comm Fail","Configure","Intf Shut",
                                   {'Name': 'I/O Timeout', 'Value': 246, 'IsSystem': True},
                                   {'Name': 'Calc Failed', 'Value': 249, 'IsSystem': True},
                                   {'Name': 'Bad', 'Value': 307, 'IsSystem': True}]):
        df = df.apply(lambda x: x.replace(bad_data, np.nan), axis=0)
        return df

    #coluna "dummies" numéricas para as famílias de papel
    def dummies_LINHA(df):

        list_fam = ['SBA', 'DUO', 'BCO', 'TWP', 'TFP', 'S6N', 'TPR', 'CBO', 'TPW','BCC','TPS'] #TPS predito como TWP
        list_dum = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 4]

        replace_values = dict(zip(list_fam,list_dum))

        df['LINHA'] = df['LINHA'].replace(replace_values)

        return df

    features = dataframe #dataframe fornecido

    #familia do cartão
    if 'LINHA' in list(features.columns.values):
        pass
    else:
        features["LINHA"] = features["B6FPGRADE"].str[0:3]

    #substituir os valores Bad Data por NaN
    features = fix_bad_data(features)

    #função dummies familia do cartão
    features = dummies_LINHA(features)

    #converter colunas (menos TIMESTAMP, LINHA e PROD) para valor numérico
    for i in list(features.columns.values):
        if i in ["TIMESTAMP","LINHA","B6FPGRADE","B6OPT_ROLO"]:
            pass
        else:
            if features[i].dtype == 'O':
                features[i] = features[i].astype('float64')

    #adicionar tags - CÁLCULO DE FLUXO DE CELULOSE EM FUNÇÃO DE OUTRAS DISPONÍVEIS
    features["GSL1"] = (features["B6MFVAT01WFPV"]*features["B6AI0405PV"])/features["B6P1XDHDRESPDAPV"]
    features["GSL4"] = (features["B6MFVAT04WFPV"]*features["B6AI0480PV"])/features["B6P1XDHDRESPDAPV"]
    features["GSL2"] = (features["B6MFVAT02WFPV"]*features["B6AI0430PV"])/features["B6P1XDHDRESPDAPV"]

    features = features.drop(columns = ["B6MFVAT01WFPV","B6MFVAT04WFPV","B6MFVAT02WFPV","B6AI0405PV",
                                        "B6AI0480PV","B6AI0430PV"])

    #filtro de quebras
    tags_quebras = ['QUEBRAS_MB6_HST','B6P1XDHD.BRKAC']
    for i in tags_quebras:
        if i in list(features.columns.values):
            features = features[features[i] == 0]
            features = features.drop(columns = [i])

    #tratar dados Infinitos
    for i in ['GSL1','GSL4','GSL2']:
        features[features[i]==np.inf]=np.nan
        features = features.dropna(axis=0)

    #excluir linha que contém valores nulos
    features = features.dropna(axis=0)

    #excluir possiveis linhas duplicadas
    features = features.drop_duplicates()

    #tags de rigidez do laboratório
    r_lab = features[['B6OPT_119_AVG','B6OPT_120_AVG']]

    #timestamp
    timestamp = features[['TIMESTAMP']]

    #tirar targets + timestamp e numero do rolo
    features = features.drop(columns = ['TIMESTAMP','B6OPT_ROLO','B6OPT_119_AVG','B6OPT_120_AVG','B6FPGRADE']) 

    return r_lab, timestamp, features

#Load no modelo de predição
def load_model(fname):
    
    with open(fname, 'rb') as ifile:
        reg = pickle.load(ifile)
        
    return reg

#Predição
def predict_r(model,tsp,feat):
    predict = model.predict(feat)

    pred = pd.DataFrame(data = predict,columns = ['B6RIGIDEZ_L_FRC','B6RIGIDEZ_T_FRC'])
    
    #Equação de Regressão Linear obtida em 21/04/2020    
    pred['L_reglin'] = pred['B6RIGIDEZ_L_FRC']*0.98164837 + 11.8311679 - 20.0
    pred['T_reglin'] = pred['B6RIGIDEZ_T_FRC']*0.94711796 + 8.50177516
    
    tsp = tsp.reset_index()
    
    return pred,tsp

#Escrever os valores nas tags de rigidez
def sending_values(webIds,pred,tsp):
    for value in range(len(pred)):
        client.stream.update_value_with_http_info(webIds[0],value = {"Timestamp": tsp["TIMESTAMP"][value],
                                                                     "Value": pred["L_reglin"][value],
                                                                     "UnitsAbbreviation": "",
                                                                     "Good": True,
                                                                     "Questionable": False})
        client.stream.update_value_with_http_info(webIds[1],value = {"Timestamp": tsp["TIMESTAMP"][value],
                                                                     "Value": pred["T_reglin"][value],
                                                                     "UnitsAbbreviation": "",
                                                                     "Good": True,
                                                                     "Questionable": False})