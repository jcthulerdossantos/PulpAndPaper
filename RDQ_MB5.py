import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import datetime
from tzlocal import get_localzone
import math

import warnings
warnings.filterwarnings("ignore")

#df de dados do PTP-AF

path_specs = #NOME DO DIRETÓRIO DAS ESPECIFICAÇÕES

df_af = pd.read_excel(path_specs + '/dir',sheet_name='dir_specs')

df_af = df_af.iloc[:,2:11].drop(columns = ['Peso'])

print('OK!')

#lista de tags
tags = ['B5OPT_015_AVG','B5OPT_061_AVG','B5OPT_090_AVG','B5OPT_091_AVG','B5OPT_104_AVG','B5OPT_117_AVG',
        'B5OPT_158_AVG','B5OPT_171_AVG','B5OPT_175_AVG','B5OPT_176_AVG',
        'B5OPT_183_AVG','B5OPT_187_AVG','B5OPT_188_AVG','B5P11BW1NPROLA',
        'B5P11CG1NPROLA','B5FI1555PV','P1CWP1VESDFV','P1CCP1VESDFV','B5OPT_GRADE_SPEC','QUEBRAS_MB5_HST']

#descrição das tags
descript = ['GRAMATURA LAB','ESTOURO FELTRO','SUJIDADE FELTRO','SUJIDADE TELA','ALVURA ISO FELTRO (C2)',
            'FLUORESCÊNCIA FELTRO','UMIDADE LAB','DENSIDADE','DESFIBRAMENTO','ABSORÇÃO ESPECÍFICA','ESPESSURA LAB',
            'CAPACIDADE ESPECÍFICA','ENERGIA DESFIBRAMENTO','GRAMATURA SCANNER',
            'ESPESSURA SCANNER','UMIDADE SCANNER','DESVIO TRANSVERSAL DE GRAMATURA',
            'DESVIO TRANSVERSAL DE ESPESSURA']

#categoria das tags
cat = ['EXTERNO','EXTERNO','EXTERNO','EXTERNO','EXTERNO','INTERNO','EXTERNO','EXTERNO','INTERNO','HISTÓRICO',
       'EXTERNO','HISTÓRICO','INTERNO','SCANNER','SCANNER','SCANNER','SCANNER','SCANNER']

print('OK!')

#conectando e extraindo dados a serem analisados
import osisoft.pidevclub.piwebapi

user= #USER PARA ACESSO
pw = #PASSWORD DO USER

from osisoft.pidevclub.piwebapi.pi_web_api_client import PIWebApiClient  
client = PIWebApiClient('https://NAME_DIR/piwebapi', False, user, pw, False) #INCLUIR NAME_DIR
path = 'NAME_DIR_LOCAL' #INCLUIR NAME_DIR_LOCAL

paths = []

for tag in tags:
    paths.append(path + tag)

#puxar dados do dia anterior a cada 1 min
df1 = client.data.get_multiple_interpolated_values(paths, start_time = '*-1440m', end_time = '*',interval = '1m')
print('OK!')

df_aux = [df1]

#pré-processamento: selecionar apenas as colunas de valores e uma coluna de Timestamp, renomear colunas dos df's
numbers = np.arange(1,(len(tags)+1),1)
value = 'Value'
list_values = ['Timestamp1']
for number in numbers:
    list_values.append(value + str(number))

tags.insert(0,'TIMESTAMP')

list_df = []

for df in df_aux:   

    df = df.loc[1:,list_values]
    
    df = df.rename(columns = dict(zip(list_values,tags)))
    
    list_df.append(df)
    
print('OK!')

#transformar em um df só
for index in range(len(list_df)):
    
    if index == 0:
        df = list_df[index]
    else:
        df = df.append(list_df[index],ignore_index = True)
        
df = df.reset_index().drop(columns = ['index'])

#excluindo períodos de quebra (influência nas tags de scanner)
df = df[df['QUEBRAS_MB5_HST'] == 0]

print('OK!')

#função para excluir bad data
def fix_bad_data(df, bad_data=["Bad Data","No Data","Bad","I/O Timeout","Calc Failed",
                               "Arc Off-line","Comm Fail","Configure","Intf Shut",
                               {'Name': 'I/O Timeout', 'Value': 246, 'IsSystem': True},
                               {'Name': 'Calc Failed', 'Value': 249, 'IsSystem': True},
                               {'Name': 'Bad', 'Value': 307, 'IsSystem': True},
                               {'Name': 'Intf Shut', 'Value': 311, 'IsSystem': True}]): #erros possíveis no sistema
    
    df = df.apply(lambda x: x.replace(bad_data, np.nan), axis=0)
    
    df = df.dropna(axis=0)
    
    return df

#vetor timestamp
aux_tsp = df[['TIMESTAMP']]

#separar diferentes df's de acordo com as diferentes os diferentes produtos - papel - produzidos
prods = df['B5OPT_GRADE_SPEC'].unique()

df_prod = []

for prod in prods:
    
    aux = df[df['B5OPT_GRADE_SPEC'] == prod]
    aux = aux.drop(columns = ['TIMESTAMP','B5OPT_GRADE_SPEC','QUEBRAS_MB5_HST'])
    aux = fix_bad_data(aux)
    aux = aux.describe().T.drop(columns = ['count']).iloc[:,:2]
    
    df_prod.append(aux)
    
print('OK!')

#intervalo de cálculo
aux_tsp = pd.to_datetime(aux_tsp['TIMESTAMP'],format = '%Y-%m-%d').to_list()
tsp = []
for dt in aux_tsp:
    tsp.append(dt.astimezone(tz = 'America/Sao_Paulo'))
    
#day_i = str(tsp[0].day) + '/' + str(tsp[0].month) + '/' + str(tsp[0].year)
day_f = str(tsp[-1].day) + '/' + str(tsp[-1].month) + '/' + str(tsp[-1].year)
#interval = day_i + ' - ' + day_f

print('OK!')

#lendo csv antigo e captando semana antiga - INCLUIR DIRETÓRIO DE LOCAIS DOS ARQUIVOS
try:
    old_df = pd.read_csv('RDQ_MB5.csv', sep = ';', decimal = ',', encoding = 'latin-1')

    old_df = old_df.iloc[:,1:]

    old_sem = sorted(list(old_df.Semana.unique()))[-1]
except:
    pass

#descobrindo a semana
df_date = pd.read_excel('data_semana.xlsx') #ARQUIVO COM NÚMEROS DAS SEMANAS
df_date = df_date[(df_date.Dia_ini <= tsp[-1].date()) & (df_date.Dia_fin >= tsp[-1].date())]
sem = df_date.Semana.values[0]

if sem == 1:
    os.remove('RDQ_MB5.csv') #ARQUIVO DE PERFORMANCE É ANUAL
else:
    pass

print('OK!')


# In[11]:


#excluindo tags de grade e quebra
#lista de tags - tags com ambos os limites, tags sem limites inferior e tags sem limites superiores

tags = ['B5OPT_015_AVG','B5OPT_061_AVG','B5OPT_090_AVG','B5OPT_091_AVG','B5OPT_104_AVG','B5OPT_117_AVG',
        'B5OPT_158_AVG','B5OPT_171_AVG','B5OPT_175_AVG','B5OPT_176_AVG','B5OPT_183_AVG','B5OPT_187_AVG',
        'B5OPT_188_AVG','B5P11BW1NPROLA','B5P11CG1NPROLA','B5FI1555PV','P1CWP1VESDFV','P1CCP1VESDFV']

tags_sem_LI = ['B5OPT_117_AVG','B5OPT_176_AVG','B5OPT_188_AVG']

tags_sem_LS = ['B5OPT_104_AVG','B5OPT_175_AVG','B5OPT_183_AVG','B5OPT_187_AVG','B5P11CG1NPROLA']

#conseguir valores do arquivo PTP-AF
for num in range(len(prods)):
    
    aux_desc = []
    aux_cat = []
    aux_unit = []
    aux_LI = []
    aux_LS = []
    aux_grade = []
    aux_dt = []
    aux_sem = []

    for index in range(len(tags)):
        
        if tags[index] == 'B5P11BW1NPROLA': #gramatura scanner - puxar spec da tag do lab    
            aux_df = df_af[(df_af['Tag'] == 'B5OPT_015_AVG') & (df_af['Grade'] == prods[num])]
        elif tags[index] == 'B5P11CG1NPROLA': #espessura scanner - puxar spec da tag do lab    
            aux_df = df_af[(df_af['Tag'] == 'B5OPT_183_AVG') & (df_af['Grade'] == prods[num])]
        elif tags[index] == 'B5FI1555PV': #umidade scanner - puxar spec da tag do lab    
            aux_df = df_af[(df_af['Tag'] == 'B5OPT_158_AVG') & (df_af['Grade'] == prods[num])]
            
        else:   
            aux_df = df_af[(df_af['Tag'] == tags[index]) & (df_af['Grade'] == prods[num])]
            
        #Descrição
        aux_desc.append(descript[index])
        
        #Categoria
        aux_cat.append(cat[index])
        
        #UM (unidade de medida)
        try:
            aux_unit.append(aux_df['UNIT'].to_list()[0])
        except:
            aux_unit.append('Unknown')
        
        #LI (limite inferior)
        if tags[index] in tags_sem_LI:
            aux_LI.append(np.nan)
        else:
            try:
                aux_LI.append(aux_df['LimInf'].to_list()[0])
            except:
                aux_LI.append(np.nan)
        
        #LS (limite superior)
        if tags[index] in tags_sem_LS:
            aux_LS.append(np.nan)
        else:
            try:
                aux_LS.append(aux_df['LimSup'].to_list()[0])
            except:
                aux_LS.append(np.nan)
        
        #Grade, Dia do Cálculo, Semana do Cálculo
        aux_grade.append(prods[num])
        aux_dt.append(day_f)
        aux_sem.append(sem)
    
    df_prod[num]['Descrição'] = aux_desc
    df_prod[num]['Categoria'] = aux_cat
    df_prod[num]['UM'] = aux_unit
    df_prod[num]['LimInf'] = aux_LI
    df_prod[num]['LimSup'] = aux_LS
    df_prod[num]['Grade'] = aux_grade
    df_prod[num]['Data'] = aux_dt
    df_prod[num]['Semana'] = aux_sem
    
print('OK!')

#cálculo de Cp e Cpk
#lista de tags

for num in range(len(df_prod)):
    
    aux_cp = []
    aux_cpk = []
    
    for index in range(len(tags)):

        df_aux = df_prod[num].loc[tags[index],:]

        if tags[index] in tags_sem_LI: #tags sem LI - não tem Cp
            cpk = (df_aux['LimSup'] - df_aux['mean'])/(3*df_aux['std'])
            aux_cp.append(np.nan)
            aux_cpk.append(cpk)
        elif tags[index] in tags_sem_LS: #tags sem LS - não tem Cp
            cpk = (df_aux['mean'] - df_aux['LimInf'])/(3*df_aux['std'])
            aux_cp.append(np.nan)
            aux_cpk.append(cpk)
        else:
            cp = (df_aux['LimSup'] - df_aux['LimInf'])/(6*df_aux['std'])
            aux_cp.append(cp)

            cpk1 = (df_aux['LimSup'] - df_aux['mean'])/(3*df_aux['std'])
            cpk2 = (df_aux['mean'] - df_aux['LimInf'])/(3*df_aux['std'])
            if cpk1 < cpk2:
                aux_cpk.append(cpk1)
            else:
                aux_cpk.append(cpk2)

    df_prod[num]['Cp'] = aux_cp
    df_prod[num]['Cpk'] = aux_cpk
    
print('OK!')

#retoques finais
for num in range(len(df_prod)):
    
    df_prod[num] = df_prod[num][['Descrição','UM','mean','std','LimInf','LimSup',
                                 'Cp','Cpk','Categoria','Grade','Data','Semana']]
    
    df_prod[num] = df_prod[num].rename(columns = {'mean': 'Média', 'std': 'DesvPad'})
    
    df_prod[num] = df_prod[num].replace([np.inf, -np.inf], np.nan)
    
    df_prod[num] = df_prod[num].reset_index().rename(columns = {'index':'Tags'})
    
print('OK!')

#juntando os df's novos com o csv velho
try:
    new_df = old_df.copy()

    for df_specprod in df_prod:
        new_df = pd.concat([new_df, df_specprod], ignore_index = True)
        
except:
    new_df = df_prod[0].copy()
    
    for index in range(len(df_prod)):
        if index == 0:
            pass
        else:
            new_df = pd.concat([new_df, df_prod[index]], ignore_index = True)
            
print('OK!')

#alterando separador de coluna e de decimal
new_df.to_csv('RDQ_MB5.csv', decimal = ',', sep = ';', encoding = 'latin-1') #INCLUIR DIRETÓRIO PARA SALVAR ARQUIVO

print('FIM!')