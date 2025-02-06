how to start an ollama server on AI Machine, that we can access remotely: sudo OLLAMA_MODELS=/usr/share/ollama/.ollama/models/ OLLAMA_HOST=0.0.0.0:9066 /usr/local/bin/ollama serve

How to set up lightrag on AI Machine:
git clone this repo : git clone URL

install all packages : 
 inside LightRAG directory
- pip install -e . #if you to setup in development mode(see changes made in packages w/o having to reinstall it again)
- pip install . #if you want to setup in production mode
- pip install fastapi 'uvicorn[standard]' python-multipart