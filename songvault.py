from json_to_mp3 import JsonToMp3
from spotify_sync_to_local import SpotifySyncToLocal


spotify_sync_to_local = SpotifySyncToLocal()
json_to_mp3 = JsonToMp3()

spotify_sync_to_local.sync()
json_to_mp3.json_to_mp3('list_data.json')
