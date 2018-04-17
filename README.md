# settings.json Explanation:
'''json
{
	# RSS Addresses
    # Format: "site nickname":"rss address",   <--!!!Remember to put Comma after it!!!
    "subscribe_address":{
            "nickname":"",
        },
    # Client Settings
    "client_settings":{
        "local":{
            # REQUIRED FIELD
            # Sites that the client is subscribing to
            "subscribe_to":[],
            # In GiB
            "free_diskspace":1000
        }
    },
    # Listening port
    "server_listening_port": 444, 
    # Server certificate path
    "server_cert_path": "server.pem", 
    # Listening address
    "server_listening_address": "0.0.0.0", 
    # Site Check Intervals. Measure in seconds
    # Format: "nickname": seconds
    "check_interval":{
        "DEFAULT":30
     },
    # Maximum Items for each site of each client
    "maximum_items_per_client":30,
    # Path of Feeds. DO NOT MODIFY IT UNLESS U KNOW WHAT U ARE DOING!!
    "path":{}
}
'''