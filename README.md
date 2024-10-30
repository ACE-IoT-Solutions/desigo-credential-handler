## Desigo Credential Handler
Until the Eclipse VOLTTRON Platform adds features for sharing data between device instances, this agent serves to minimize open sessions on the target Desigo Server

### Configuration
```json
{                                                                       
"token_timeout": 300,                                                   
"servers": [                                                            
    {                                                                   
    "user": "domain\\user",                                
    "password": "password",                                         
    "url": "https://<server-host>:<port>/<api-path>"
    }                                                                   
  ]                                                                     
}                                                                       
```