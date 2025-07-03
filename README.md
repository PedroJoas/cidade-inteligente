#  Cidade Inteligente - Sistemas Distribuídos (2025.1)

Projeto desenvolvido como parte da disciplina de Sistemas Distribuídos. O sistema simula uma **cidade inteligente** com comunicação entre **clientes**, **gateway central**, **sensores** e **atuadores**, utilizando **sockets TCP/UDP**, **multicast** e **Protocol Buffers**.

---

## 📌 Funcionalidades

- 🔁 **Descoberta automática** de dispositivos via multicast UDP.
- 🛰️ **Sensores** enviando dados periódicos para o gateway via UDP.
- 🚦 **Atuadores** recebem comandos do gateway via TCP.
- 📋 **Cliente interativo** que lista dispositivos e envia comandos.
- 🧠 **Gateway** que gerencia todos os dispositivos conectados.

---

## 🗂️ Estrutura do Projeto
cidade-inteligente/
├── cliente.py # Cliente interativo (menu de comandos)
├── gateway.py # Gateway central (gerencia sensores/atuadores)
├── dispositivos/
│ ├── sensor_temperatura.py # Envia dados periódicos via UDP
│ └── semaforo.py # Atuador que responde a comandos TCP
├── protos/
│ ├── cliente_gateway.proto
│ ├── cliente_gateway_pb2.py
│ ├── gateway_atuadores.proto
│ ├── gateway_atuadores_pb2.py
├── utils/
│ └── multicast.py # Funções para envio/recepção multicast
└── README.md

