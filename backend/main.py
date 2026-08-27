import requests

url = "https://api.infosimples.com/api/v2/consultas/sefaz/sp/cfe-completa"

payload = 'chave=35250145495694001276590000300919739987647294&token=4ROc5LdDAEtAWjs52SJ1FfjfF4RVh-12lJP8OFKq'
headers = {
  'Content-Type': 'application/x-www-form-urlencoded',
  'Content-Type': 'application/x-www-form-urlencoded'
}

response = requests.request("POST", url, headers=headers, data=payload)

print(response.text)