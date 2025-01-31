from pymilvus import connections, db

conn = connections.connect(host="localhost", port="19530")
# database = db.create_database("lightrag")
database = db.create_database("lightrag2")


# from pymilvus import connections, Role

# _URI = "https://in03-0188093ded1ad88.serverless.gcp-us-west1.cloud.zilliz.com"
# _TOKEN = "4e3b66ef493ea0333293f5f1a85366d2142d4e83d6117c64aa31a0185961cd96bb0331df417cfbf65a2818dbdd429c573c61973c"
# _DB_NAME = "lightrag"


# def connect_to_milvus(db_name="default"):
#     print(f"connect to milvus\n")
#     connections.connect(
#         user="db_0188093ded1ad88",
#         password="Yp6(hN{,]/,LJXJ8",
#         uri=_URI,
#         token=_TOKEN,
#     )
# connect_to_milvus()
# database = db.create_database("lightrag")