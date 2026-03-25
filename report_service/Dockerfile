FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY src /app
COPY tests /app/tests
COPY examples /app/examples
COPY pytest.ini /app/pytest.ini
COPY form_d.html /app/form_d.html
COPY prompt_conversion_dps_new_2026.txt /app/prompt_conversion_dps_new_2026.txt
EXPOSE 8085
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8085"]
