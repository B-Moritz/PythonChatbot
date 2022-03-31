# Build command used from within the PythonChatbot foleder:
#  docker build -f Dockerfile .. -t berntolsen/pythonchatserver:1.0
FROM ubuntu
RUN apt -y update
RUN apt-get install -y python3
RUN mkdir /PythonChatbot
COPY PythonChatbot/ /PythonChatbot
