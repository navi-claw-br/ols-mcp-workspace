FROM php:8.3-cli-alpine

WORKDIR /app
COPY index.php .

EXPOSE 8080
USER 1001

CMD ["php", "-S", "0.0.0.0:8080", "index.php"]
