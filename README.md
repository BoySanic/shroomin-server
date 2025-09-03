# Usage

First, copy example.env to .env and change any relevant values within .env to customize your deployment

In the repo root directory:
```
docker compose up --build -d
```

If there are no errors:

shroomin-mkproject will run a shell script to create the db and table usig init.sql
shroom-webserver and shroom-checker will launch after postgres is ready
localhost:5000 will be open for web requests



# How to set this up on the client side

In client.py, change the example.com to either your public ip, the ip of your vps running shroomin-server, etc. Whatever it is, not our problem.

Run client.py with the seeds file set to whatever the absolute or relative path of the seeds output file is.

For vast.ai, I've had a lot of success with splitting the tmux session into two separate terminals and running the client in one terminal while the gpu program runs in the other.

If you get status 200 from the web server, it accepted your seeds.

Check what you got with `select * from table_name;` in postgres.

Easiest way to access postgres is via `docker exec -it shroomin-postgres psql -U postgres -d db_name` where you replace db_name with whatever the db name is ("mushroom" by default)


Good luck, and happy shroomin.

I can help in the discord server for any specific sql queries you're interested in.