#!/bin/bash

# ====================================
# Script para popular TODOS os 184 municípios do Ceará
# Dados: IBGE 2024
# ====================================

echo "🏙️  Populando TODOS os 184 municípios do Ceará..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Array com TODOS os 184 municípios do Ceará
declare -a MUNICIPIOS=(
  '{"name": "Abaiara", "state": "CE", "year": 2025, "population": 11441, "ibge_code": "2300101"}'
  '{"name": "Acarape", "state": "CE", "year": 2025, "population": 16843, "ibge_code": "2300150"}'
  '{"name": "Acaraú", "state": "CE", "year": 2025, "population": 63905, "ibge_code": "2300200"}'
  '{"name": "Acopiara", "state": "CE", "year": 2025, "population": 56299, "ibge_code": "2300309"}'
  '{"name": "Aiuaba", "state": "CE", "year": 2025, "population": 17255, "ibge_code": "2300408"}'
  '{"name": "Alcântaras", "state": "CE", "year": 2025, "population": 10551, "ibge_code": "2300507"}'
  '{"name": "Altaneira", "state": "CE", "year": 2025, "population": 7226, "ibge_code": "2300606"}'
  '{"name": "Alto Santo", "state": "CE", "year": 2025, "population": 18240, "ibge_code": "2300705"}'
  '{"name": "Amontada", "state": "CE", "year": 2025, "population": 44552, "ibge_code": "2300754"}'
  '{"name": "Antonina do Norte", "state": "CE", "year": 2025, "population": 7236, "ibge_code": "2300804"}'
  '{"name": "Apuiarés", "state": "CE", "year": 2025, "population": 15890, "ibge_code": "2300903"}'
  '{"name": "Aquiraz", "state": "CE", "year": 2025, "population": 84420, "ibge_code": "2301000"}'
  '{"name": "Aracati", "state": "CE", "year": 2025, "population": 74981, "ibge_code": "2301109"}'
  '{"name": "Aracoiaba", "state": "CE", "year": 2025, "population": 27007, "ibge_code": "2301208"}'
  '{"name": "Ararendá", "state": "CE", "year": 2025, "population": 11182, "ibge_code": "2301257"}'
  '{"name": "Araripe", "state": "CE", "year": 2025, "population": 22067, "ibge_code": "2301307"}'
  '{"name": "Aratuba", "state": "CE", "year": 2025, "population": 11911, "ibge_code": "2301406"}'
  '{"name": "Arneiroz", "state": "CE", "year": 2025, "population": 7817, "ibge_code": "2301505"}'
  '{"name": "Assaré", "state": "CE", "year": 2025, "population": 24358, "ibge_code": "2301604"}'
  '{"name": "Aurora", "state": "CE", "year": 2025, "population": 25702, "ibge_code": "2301703"}'
  '{"name": "Baixio", "state": "CE", "year": 2025, "population": 9219, "ibge_code": "2301802"}'
  '{"name": "Banabuiú", "state": "CE", "year": 2025, "population": 19046, "ibge_code": "2301851"}'
  '{"name": "Barbalha", "state": "CE", "year": 2025, "population": 61449, "ibge_code": "2301901"}'
  '{"name": "Barreira", "state": "CE", "year": 2025, "population": 21214, "ibge_code": "2301950"}'
  '{"name": "Barro", "state": "CE", "year": 2025, "population": 22380, "ibge_code": "2302008"}'
  '{"name": "Barroquinha", "state": "CE", "year": 2025, "population": 17446, "ibge_code": "2302057"}'
  '{"name": "Baturité", "state": "CE", "year": 2025, "population": 35388, "ibge_code": "2302107"}'
  '{"name": "Beberibe", "state": "CE", "year": 2025, "population": 52061, "ibge_code": "2302206"}'
  '{"name": "Bela Cruz", "state": "CE", "year": 2025, "population": 33519, "ibge_code": "2302305"}'
  '{"name": "Boa Viagem", "state": "CE", "year": 2025, "population": 54604, "ibge_code": "2302404"}'
  '{"name": "Brejo Santo", "state": "CE", "year": 2025, "population": 48571, "ibge_code": "2302503"}'
  '{"name": "Camocim", "state": "CE", "year": 2025, "population": 65456, "ibge_code": "2302602"}'
  '{"name": "Campos Sales", "state": "CE", "year": 2025, "population": 28997, "ibge_code": "2302701"}'
  '{"name": "Canindé", "state": "CE", "year": 2025, "population": 78114, "ibge_code": "2302800"}'
  '{"name": "Capistrano", "state": "CE", "year": 2025, "population": 17348, "ibge_code": "2302909"}'
  '{"name": "Caridade", "state": "CE", "year": 2025, "population": 21318, "ibge_code": "2303006"}'
  '{"name": "Cariré", "state": "CE", "year": 2025, "population": 19798, "ibge_code": "2303105"}'
  '{"name": "Caririaçu", "state": "CE", "year": 2025, "population": 27792, "ibge_code": "2303204"}'
  '{"name": "Cariús", "state": "CE", "year": 2025, "population": 18864, "ibge_code": "2303303"}'
  '{"name": "Carnaubal", "state": "CE", "year": 2025, "population": 17626, "ibge_code": "2303402"}'
  '{"name": "Cascavel", "state": "CE", "year": 2025, "population": 73216, "ibge_code": "2303501"}'
  '{"name": "Catarina", "state": "CE", "year": 2025, "population": 21509, "ibge_code": "2303600"}'
  '{"name": "Catunda", "state": "CE", "year": 2025, "population": 11226, "ibge_code": "2303659"}'
  '{"name": "Caucaia", "state": "CE", "year": 2025, "population": 368918, "ibge_code": "2303709"}'
  '{"name": "Cedro", "state": "CE", "year": 2025, "population": 26125, "ibge_code": "2303808"}'
  '{"name": "Chaval", "state": "CE", "year": 2025, "population": 14272, "ibge_code": "2303907"}'
  '{"name": "Choró", "state": "CE", "year": 2025, "population": 13927, "ibge_code": "2303931"}'
  '{"name": "Chorozinho", "state": "CE", "year": 2025, "population": 19562, "ibge_code": "2303956"}'
  '{"name": "Coreaú", "state": "CE", "year": 2025, "population": 22055, "ibge_code": "2304004"}'
  '{"name": "Crateús", "state": "CE", "year": 2025, "population": 76142, "ibge_code": "2304103"}'
  '{"name": "Crato", "state": "CE", "year": 2025, "population": 133031, "ibge_code": "2304202"}'
  '{"name": "Croatá", "state": "CE", "year": 2025, "population": 18360, "ibge_code": "2304236"}'
  '{"name": "Cruz", "state": "CE", "year": 2025, "population": 24221, "ibge_code": "2304251"}'
  '{"name": "Deputado Irapuan Pinheiro", "state": "CE", "year": 2025, "population": 8058, "ibge_code": "2304269"}'
  '{"name": "Ererê", "state": "CE", "year": 2025, "population": 6498, "ibge_code": "2304277"}'
  '{"name": "Eusébio", "state": "CE", "year": 2025, "population": 54791, "ibge_code": "2304285"}'
  '{"name": "Farias Brito", "state": "CE", "year": 2025, "population": 19316, "ibge_code": "2304301"}'
  '{"name": "Forquilha", "state": "CE", "year": 2025, "population": 23174, "ibge_code": "2304350"}'
  '{"name": "Fortaleza", "state": "CE", "year": 2025, "population": 2700000, "ibge_code": "2304400"}'
  '{"name": "Fortim", "state": "CE", "year": 2025, "population": 16397, "ibge_code": "2304459"}'
  '{"name": "Frecheirinha", "state": "CE", "year": 2025, "population": 13101, "ibge_code": "2304509"}'
  '{"name": "General Sampaio", "state": "CE", "year": 2025, "population": 6339, "ibge_code": "2304608"}'
  '{"name": "Graça", "state": "CE", "year": 2025, "population": 16165, "ibge_code": "2304657"}'
  '{"name": "Granja", "state": "CE", "year": 2025, "population": 54520, "ibge_code": "2304707"}'
  '{"name": "Granjeiro", "state": "CE", "year": 2025, "population": 4650, "ibge_code": "2304806"}'
  '{"name": "Groaíras", "state": "CE", "year": 2025, "population": 10822, "ibge_code": "2304905"}'
  '{"name": "Guaiúba", "state": "CE", "year": 2025, "population": 27786, "ibge_code": "2304954"}'
  '{"name": "Guaraciaba do Norte", "state": "CE", "year": 2025, "population": 40838, "ibge_code": "2305001"}'
  '{"name": "Guaramiranga", "state": "CE", "year": 2025, "population": 4313, "ibge_code": "2305100"}'
  '{"name": "Hidrolândia", "state": "CE", "year": 2025, "population": 19063, "ibge_code": "2305209"}'
  '{"name": "Horizonte", "state": "CE", "year": 2025, "population": 67203, "ibge_code": "2305233"}'
  '{"name": "Ibaretama", "state": "CE", "year": 2025, "population": 13049, "ibge_code": "2305266"}'
  '{"name": "Ibiapina", "state": "CE", "year": 2025, "population": 26166, "ibge_code": "2305308"}'
  '{"name": "Ibicuitinga", "state": "CE", "year": 2025, "population": 12470, "ibge_code": "2305332"}'
  '{"name": "Icapuí", "state": "CE", "year": 2025, "population": 20115, "ibge_code": "2305357"}'
  '{"name": "Icó", "state": "CE", "year": 2025, "population": 68170, "ibge_code": "2305407"}'
  '{"name": "Iguatu", "state": "CE", "year": 2025, "population": 103259, "ibge_code": "2305506"}'
  '{"name": "Independência", "state": "CE", "year": 2025, "population": 26865, "ibge_code": "2305605"}'
  '{"name": "Ipaporanga", "state": "CE", "year": 2025, "population": 11985, "ibge_code": "2305654"}'
  '{"name": "Ipaumirim", "state": "CE", "year": 2025, "population": 13423, "ibge_code": "2305704"}'
  '{"name": "Ipu", "state": "CE", "year": 2025, "population": 42342, "ibge_code": "2305803"}'
  '{"name": "Ipueiras", "state": "CE", "year": 2025, "population": 40458, "ibge_code": "2305902"}'
  '{"name": "Iracema", "state": "CE", "year": 2025, "population": 13005, "ibge_code": "2306009"}'
  '{"name": "Irauçuba", "state": "CE", "year": 2025, "population": 23422, "ibge_code": "2306108"}'
  '{"name": "Itaiçaba", "state": "CE", "year": 2025, "population": 7595, "ibge_code": "2306207"}'
  '{"name": "Itaitinga", "state": "CE", "year": 2025, "population": 41479, "ibge_code": "2306256"}'
  '{"name": "Itapajé", "state": "CE", "year": 2025, "population": 68820, "ibge_code": "2306306"}'
  '{"name": "Itapipoca", "state": "CE", "year": 2025, "population": 132179, "ibge_code": "2306405"}'
  '{"name": "Itapiúna", "state": "CE", "year": 2025, "population": 20187, "ibge_code": "2306504"}'
  '{"name": "Itarema", "state": "CE", "year": 2025, "population": 40098, "ibge_code": "2306553"}'
  '{"name": "Itatira", "state": "CE", "year": 2025, "population": 20085, "ibge_code": "2306603"}'
  '{"name": "Jaguaretama", "state": "CE", "year": 2025, "population": 18989, "ibge_code": "2306702"}'
  '{"name": "Jaguaribara", "state": "CE", "year": 2025, "population": 11902, "ibge_code": "2306801"}'
  '{"name": "Jaguaribe", "state": "CE", "year": 2025, "population": 36604, "ibge_code": "2306900"}'
  '{"name": "Jaguaruana", "state": "CE", "year": 2025, "population": 35712, "ibge_code": "2307007"}'
  '{"name": "Jardim", "state": "CE", "year": 2025, "population": 27913, "ibge_code": "2307106"}'
  '{"name": "Jati", "state": "CE", "year": 2025, "population": 8238, "ibge_code": "2307205"}'
  '{"name": "Jijoca de Jericoacoara", "state": "CE", "year": 2025, "population": 20269, "ibge_code": "2307254"}'
  '{"name": "Juazeiro do Norte", "state": "CE", "year": 2025, "population": 276264, "ibge_code": "2307304"}'
  '{"name": "Jucás", "state": "CE", "year": 2025, "population": 25642, "ibge_code": "2307403"}'
  '{"name": "Lavras da Mangabeira", "state": "CE", "year": 2025, "population": 34076, "ibge_code": "2307502"}'
  '{"name": "Limoeiro do Norte", "state": "CE", "year": 2025, "population": 59412, "ibge_code": "2307601"}'
  '{"name": "Madalena", "state": "CE", "year": 2025, "population": 19446, "ibge_code": "2307635"}'
  '{"name": "Maracanaú", "state": "CE", "year": 2025, "population": 228712, "ibge_code": "2307650"}'
  '{"name": "Maranguape", "state": "CE", "year": 2025, "population": 131123, "ibge_code": "2307700"}'
  '{"name": "Marco", "state": "CE", "year": 2025, "population": 27269, "ibge_code": "2307809"}'
  '{"name": "Martinópole", "state": "CE", "year": 2025, "population": 11227, "ibge_code": "2307908"}'
  '{"name": "Massapê", "state": "CE", "year": 2025, "population": 37089, "ibge_code": "2308005"}'
  '{"name": "Mauriti", "state": "CE", "year": 2025, "population": 47842, "ibge_code": "2308104"}'
  '{"name": "Meruoca", "state": "CE", "year": 2025, "population": 14824, "ibge_code": "2308203"}'
  '{"name": "Milagres", "state": "CE", "year": 2025, "population": 29755, "ibge_code": "2308302"}'
  '{"name": "Milhã", "state": "CE", "year": 2025, "population": 13173, "ibge_code": "2308351"}'
  '{"name": "Miraíma", "state": "CE", "year": 2025, "population": 12871, "ibge_code": "2308377"}'
  '{"name": "Missão Velha", "state": "CE", "year": 2025, "population": 36298, "ibge_code": "2308401"}'
  '{"name": "Mombaça", "state": "CE", "year": 2025, "population": 43683, "ibge_code": "2308500"}'
  '{"name": "Monsenhor Tabosa", "state": "CE", "year": 2025, "population": 18049, "ibge_code": "2308609"}'
  '{"name": "Morada Nova", "state": "CE", "year": 2025, "population": 64409, "ibge_code": "2308708"}'
  '{"name": "Moraújo", "state": "CE", "year": 2025, "population": 8232, "ibge_code": "2308807"}'
  '{"name": "Morrinhos", "state": "CE", "year": 2025, "population": 23292, "ibge_code": "2308906"}'
  '{"name": "Mucambo", "state": "CE", "year": 2025, "population": 15207, "ibge_code": "2309003"}'
  '{"name": "Mulungu", "state": "CE", "year": 2025, "population": 12808, "ibge_code": "2309102"}'
  '{"name": "Nova Olinda", "state": "CE", "year": 2025, "population": 15797, "ibge_code": "2309201"}'
  '{"name": "Nova Russas", "state": "CE", "year": 2025, "population": 31921, "ibge_code": "2309300"}'
  '{"name": "Novo Oriente", "state": "CE", "year": 2025, "population": 28456, "ibge_code": "2309409"}'
  '{"name": "Ocara", "state": "CE", "year": 2025, "population": 26354, "ibge_code": "2309458"}'
  '{"name": "Orós", "state": "CE", "year": 2025, "population": 21389, "ibge_code": "2309508"}'
  '{"name": "Pacajus", "state": "CE", "year": 2025, "population": 76424, "ibge_code": "2309607"}'
  '{"name": "Pacatuba", "state": "CE", "year": 2025, "population": 84701, "ibge_code": "2309706"}'
  '{"name": "Pacoti", "state": "CE", "year": 2025, "population": 12661, "ibge_code": "2309805"}'
  '{"name": "Pacujá", "state": "CE", "year": 2025, "population": 6413, "ibge_code": "2309904"}'
  '{"name": "Palhano", "state": "CE", "year": 2025, "population": 9296, "ibge_code": "2310001"}'
  '{"name": "Palmácia", "state": "CE", "year": 2025, "population": 13265, "ibge_code": "2310100"}'
  '{"name": "Paracuru", "state": "CE", "year": 2025, "population": 36531, "ibge_code": "2310209"}'
  '{"name": "Paraipaba", "state": "CE", "year": 2025, "population": 33406, "ibge_code": "2310258"}'
  '{"name": "Parambu", "state": "CE", "year": 2025, "population": 32024, "ibge_code": "2310308"}'
  '{"name": "Paramoti", "state": "CE", "year": 2025, "population": 12323, "ibge_code": "2310407"}'
  '{"name": "Pedra Branca", "state": "CE", "year": 2025, "population": 43261, "ibge_code": "2310506"}'
  '{"name": "Penaforte", "state": "CE", "year": 2025, "population": 8970, "ibge_code": "2310605"}'
  '{"name": "Pentecoste", "state": "CE", "year": 2025, "population": 37364, "ibge_code": "2310704"}'
  '{"name": "Pereiro", "state": "CE", "year": 2025, "population": 16118, "ibge_code": "2310803"}'
  '{"name": "Pindoretama", "state": "CE", "year": 2025, "population": 20183, "ibge_code": "2310852"}'
  '{"name": "Piquet Carneiro", "state": "CE", "year": 2025, "population": 17183, "ibge_code": "2310902"}'
  '{"name": "Pires Ferreira", "state": "CE", "year": 2025, "population": 10922, "ibge_code": "2310951"}'
  '{"name": "Poranga", "state": "CE", "year": 2025, "population": 12076, "ibge_code": "2311009"}'
  '{"name": "Porteiras", "state": "CE", "year": 2025, "population": 16051, "ibge_code": "2311108"}'
  '{"name": "Potengi", "state": "CE", "year": 2025, "population": 11073, "ibge_code": "2311207"}'
  '{"name": "Potiretama", "state": "CE", "year": 2025, "population": 10208, "ibge_code": "2311231"}'
  '{"name": "Quiterianópolis", "state": "CE", "year": 2025, "population": 21024, "ibge_code": "2311264"}'
  '{"name": "Quixadá", "state": "CE", "year": 2025, "population": 88402, "ibge_code": "2311306"}'
  '{"name": "Quixelô", "state": "CE", "year": 2025, "population": 15350, "ibge_code": "2311355"}'
  '{"name": "Quixeramobim", "state": "CE", "year": 2025, "population": 79356, "ibge_code": "2311405"}'
  '{"name": "Quixeré", "state": "CE", "year": 2025, "population": 22203, "ibge_code": "2311504"}'
  '{"name": "Redenção", "state": "CE", "year": 2025, "population": 27752, "ibge_code": "2311603"}'
  '{"name": "Reriutaba", "state": "CE", "year": 2025, "population": 20448, "ibge_code": "2311702"}'
  '{"name": "Russas", "state": "CE", "year": 2025, "population": 77288, "ibge_code": "2311801"}'
  '{"name": "Saboeiro", "state": "CE", "year": 2025, "population": 16494, "ibge_code": "2311900"}'
  '{"name": "Salitre", "state": "CE", "year": 2025, "population": 17439, "ibge_code": "2311959"}'
  '{"name": "Santa Quitéria", "state": "CE", "year": 2025, "population": 45309, "ibge_code": "2312007"}'
  '{"name": "Santana do Acaraú", "state": "CE", "year": 2025, "population": 32244, "ibge_code": "2312106"}'
  '{"name": "Santana do Cariri", "state": "CE", "year": 2025, "population": 18163, "ibge_code": "2312205"}'
  '{"name": "São Benedito", "state": "CE", "year": 2025, "population": 46941, "ibge_code": "2312304"}'
  '{"name": "São Gonçalo do Amarante", "state": "CE", "year": 2025, "population": 50820, "ibge_code": "2312403"}'
  '{"name": "São João do Jaguaribe", "state": "CE", "year": 2025, "population": 7182, "ibge_code": "2312502"}'
  '{"name": "São Luís do Curu", "state": "CE", "year": 2025, "population": 13536, "ibge_code": "2312601"}'
  '{"name": "Senador Pompeu", "state": "CE", "year": 2025, "population": 27301, "ibge_code": "2312700"}'
  '{"name": "Senador Sá", "state": "CE", "year": 2025, "population": 7339, "ibge_code": "2312809"}'
  '{"name": "Sobral", "state": "CE", "year": 2025, "population": 210711, "ibge_code": "2312908"}'
  '{"name": "Solonópole", "state": "CE", "year": 2025, "population": 17860, "ibge_code": "2313005"}'
  '{"name": "Tabuleiro do Norte", "state": "CE", "year": 2025, "population": 30979, "ibge_code": "2313104"}'
  '{"name": "Tamboril", "state": "CE", "year": 2025, "population": 26263, "ibge_code": "2313203"}'
  '{"name": "Tarrafas", "state": "CE", "year": 2025, "population": 9399, "ibge_code": "2313252"}'
  '{"name": "Tauá", "state": "CE", "year": 2025, "population": 58641, "ibge_code": "2313302"}'
  '{"name": "Tejuçuoca", "state": "CE", "year": 2025, "population": 18519, "ibge_code": "2313351"}'
  '{"name": "Tianguá", "state": "CE", "year": 2025, "population": 75324, "ibge_code": "2313401"}'
  '{"name": "Trairi", "state": "CE", "year": 2025, "population": 55164, "ibge_code": "2313500"}'
  '{"name": "Tururu", "state": "CE", "year": 2025, "population": 16506, "ibge_code": "2313559"}'
  '{"name": "Ubajara", "state": "CE", "year": 2025, "population": 35036, "ibge_code": "2313609"}'
  '{"name": "Umari", "state": "CE", "year": 2025, "population": 7614, "ibge_code": "2313708"}'
  '{"name": "Umirim", "state": "CE", "year": 2025, "population": 20150, "ibge_code": "2313757"}'
  '{"name": "Uruburetama", "state": "CE", "year": 2025, "population": 20182, "ibge_code": "2313807"}'
  '{"name": "Uruoca", "state": "CE", "year": 2025, "population": 13933, "ibge_code": "2313906"}'
  '{"name": "Varjota", "state": "CE", "year": 2025, "population": 18814, "ibge_code": "2313955"}'
  '{"name": "Várzea Alegre", "state": "CE", "year": 2025, "population": 41051, "ibge_code": "2314003"}'
  '{"name": "Viçosa do Ceará", "state": "CE", "year": 2025, "population": 58980, "ibge_code": "2314102"}'
)

# Contador
SUCCESS=0
FAILED=0
TOTAL=${#MUNICIPIOS[@]}

echo "📊 Total de municípios a inserir: $TOTAL"
echo ""

for MUNICIPIO in "${MUNICIPIOS[@]}"; do
    NAME=$(echo "$MUNICIPIO" | python3 -c "import sys, json; print(json.load(sys.stdin)['name'])")
    printf "%-35s" "Criando $NAME..."
    
    RESPONSE=$(curl -s -X POST http://localhost:4001/api/municipalities/ \
      -H "Content-Type: application/json" \
      -d "$MUNICIPIO")
    
    if echo "$RESPONSE" | grep -q '"id"'; then
        echo "✅"
        ((SUCCESS++))
    else
        echo "❌"
        ((FAILED++))
    fi
    
    # Pequeno delay para não sobrecarregar
    sleep 0.1
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Resultado Final:"
echo ""
echo "   Total de municípios: $TOTAL"
echo "   ✅ Criados com sucesso: $SUCCESS"
echo "   ❌ Falhas ou duplicados: $FAILED"
echo ""
if [ $SUCCESS -eq $TOTAL ]; then
    echo "   🎉 Todos os municípios do Ceará foram cadastrados!"
fi
echo ""
echo "🔍 Para verificar todos os municípios cadastrados:"
echo "   make municipios-listar"
echo "   ou"
echo "   curl http://localhost:4001/api/municipalities/"
echo ""
echo "🌐 Acesse o frontend: http://localhost:4000"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

