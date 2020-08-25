import predict_rigidez_and_write_tags as Pv2_ #SEGUNDO MODELO - COM BIAS DE CORREÇÃO ! ! !

webIds = Pv2_.web_ids()
print('OK 1/7')

lv = Pv2_.last_prediction(webIds)
print('OK 2/7')

df = Pv2_.extracting_data(lv)
print('OK 3/7')

r_lab, tsp, feat = Pv2_.prepare_df(df)
print('OK 4/7')

modelo_v2 = Pv2_.load_model('DIR_MODELO_PKL' + '\\predict_rigidez')
print('OK 5/7')

pred,tsp = Pv2_.predict_r(modelo_v2,tsp,feat)
print('OK 6/7')

Pv2_.sending_values(webIds,pred,tsp)
print('OK 7/7')