FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

ENV PORT=5010
ENV PPLX_OPENAI_KEY="your-secret-api-key"
ENV COOKIES_FILE="cookies.txt"
ENV LANGUAGE="en-US"
ENV INCOGNITO="false"
ENV SOURCES=""
ENV PREFIX="perplexity-chat"


CMD python app.py \
    --port ${PORT} \
    --api-key ${PPLX_OPENAI_KEY} \
    --cookies-file ${COOKIES_FILE} \
    --language ${LANGUAGE} \
    $( [ "${INCOGNITO}" = "true" ] && echo "--incognito" ) \
    $( [ -n "${SOURCES}" ] && echo "--sources ${SOURCES}" ) \
    --prefix ${PREFIX} 
