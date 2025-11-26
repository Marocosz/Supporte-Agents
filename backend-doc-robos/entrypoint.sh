#!/bin/sh

# Armazena a porta externa em uma variável (opcional, para clareza)
HOST_PORT=8000

# Exibe a mensagem de boas-vindas formatada
echo ""
echo "============================================================"
echo "🚀 Servidor Gunicorn pronto para iniciar!"
echo "✅ Aplicação estará acessível em:"
echo "   👉 http://localhost:${HOST_PORT}"
echo "============================================================"
echo ""

# 'exec "$@"' executa o comando que foi passado como CMD no Dockerfile.
# No nosso caso, ele vai executar o comando do Gunicorn.
exec "$@"