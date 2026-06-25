FROM python:3.12-alpine3.20

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apk add --no-cache --virtual .build-deps gcc musl-dev postgresql-dev \
    && pip install pipenv

COPY Pipfile Pipfile.lock ./
RUN pipenv install --deploy --system

RUN apk add --no-cache postgresql-libs \
    && apk del .build-deps

COPY ./app /app

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]