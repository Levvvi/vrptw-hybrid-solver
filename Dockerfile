FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY apps ./apps
COPY configs ./configs
COPY tests/fixtures ./tests/fixtures

RUN python -m pip install --upgrade pip \
    && python -m pip install -e . streamlit folium streamlit-folium

EXPOSE 8501

CMD ["streamlit", "run", "apps/streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501"]
