import httplib2, urllib

class Service:
  def __init__(self,host,protocol="http",port="80"):
    self.host=host
    self.protocol=protocol
    if protocol=="https" and port=="80":
	port="443"
    self.port=port

  def sendRequest(self,service,method="GET",reference="",type="text/plain",authenticated=False,credentials="",debug=False):
    webservice = httplib2.Http()
    url = self.protocol+"://"+self.host+":"+self.port+"/"+urllib.quote("/".join(service),safe="%/:=&?~#+!$,;'@()*[]")
    headers={"Content-Type":type}
    if authenticated:
      credentials = credentials.split(":")
      webservice.add_credentials(credentials[0],credentials[1])
    if reference != "" and method=="POST":
      t=reference.split("&")
      t2=[]
      for tt in t:
	t2.append(tt.split("="))
      try:
	      data=urllib.urlencode(dict(t2))
      except ValueError:
	      data=reference
    else:
      data=reference
    if debug:
	return url
    else:
      headers,data = webservice.request(url,body=data,method=method,headers=headers)
      return data
