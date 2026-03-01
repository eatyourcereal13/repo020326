ТУТОРИАЛ

НАСТРАИВАЕМ СЕРВЕР
ЕСЛИ СЕРВЕР НОВЫЙ
ЗАХОДИМ НА СЕРВЕР

ssh ПОЛЬЗОВАТЕЛЬ@АДРЕС
Пароль вставлять правой кнопкой мыши
ДАЛЬШЕ КОМАНДЫ

1. sudo apt update && sudo apt upgrade -y
2. curl -fsSL https://get.docker.com -o get-docker.sh
3. sudo sh get-docker.sh
4. sudo usermod -aG docker $USER
5. newgrp docker
6. sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
7. mkdir bot && cd bot
8. git clone https://github.com/eatyourcereal13/repo020326.git
9. docker-compose up -d

Перед 8 и 9 шагом необходима настройка
В папке bot
1. nano .env

В .env файле ввести следующее

BOT_TOKEN=ваш токен - получать в BotFather -> /newbot 
ADMIN_IDS=id администраторов через запятую без пробелов - получать в @userinfobot
ALLOWED_GROUPS=id групп(-ы), которые(-ая) будет добавлять бота - получать в получать в @userinfobot (ГРУППА)

DB_NAME=pirate_db
DB_USER=postgres
DB_PASSWORD=postgres123
DB_HOST=postgres
DB_PORT=5432

POSTGRES_DB=pirate_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres123

Доп команды
1. Чтобы остановить
docker-compose down
2. Чтобы остановить + УДАЛИТЬ ВСЕ ДАННЫЕ
docker-compose down -v
3. Запустить 
docker-compose up -d
4. Проверить
docker ps - Если написано везде Up, то все ок

