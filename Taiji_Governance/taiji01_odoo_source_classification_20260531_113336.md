# taiji01 Odoo source classification
2026-05-31T11:33:36+00:00

## running container source
ConfigFiles=/home/taiji_01/Taiji_Hub/Taiji_Odoo/docker-compose.yml
WorkingDir=/home/taiji_01/Taiji_Hub/Taiji_Odoo
Mounts=[{"Type":"bind","Source":"/home/taiji_01/Taiji_Hub/Taiji_Odoo/addons","Destination":"/mnt/extra-addons","Mode":"rw","RW":true,"Propagation":"rprivate"},{"Type":"bind","Source":"/home/taiji_01/Taiji_Hub/Taiji_Odoo/odoo_data","Destination":"/var/lib/odoo","Mode":"rw","RW":true,"Propagation":"rprivate"}]

## compose candidates

### /home/taiji_admin/Taiji_Hub_Community/Taiji_Odoo/docker-compose.yml
version: '3.1'
services:
  wuchang_web:
    image: odoo:18.0
    container_name: wuchang_os_odoo_18
    depends_on:
      - wuchang_db
    ports:
      - "8069:8069"
    volumes:
      - ./addons:/mnt/extra-addons
      - ./odoo_data:/var/lib/odoo
    environment:
      - HOST=wuchang_db
      - USER=odoo
      - PASSWORD=taiji_secret
    restart: always
    networks:
      - wuchang_network

  wuchang_db:
    image: postgres:15
    container_name: wuchang_os_pg
    environment:
      - POSTGRES_DB=postgres
      - POSTGRES_PASSWORD=taiji_secret
      - POSTGRES_USER=odoo
    volumes:
      - ./postgres_data:/var/lib/postgresql/data
    restart: always
    networks:
      - wuchang_network

networks:
  wuchang_network:
    name: wuchang_isolated_net_18

### /home/taiji_admin/Taiji_Hub_Coffee/Taiji_Odoo/docker-compose.yml
version: '3.1'
services:
  wuchang_web:
    image: odoo:18.0
    container_name: wuchang_os_odoo_18
    depends_on:
      - wuchang_db
    ports:
      - "8069:8069"
    volumes:
      - ./addons:/mnt/extra-addons
      - ./odoo_data:/var/lib/odoo
    environment:
      - HOST=wuchang_db
      - USER=odoo
      - PASSWORD=taiji_secret
    restart: always
    networks:
      - wuchang_network

  wuchang_db:
    image: postgres:15
    container_name: wuchang_os_pg
    environment:
      - POSTGRES_DB=postgres
      - POSTGRES_PASSWORD=taiji_secret
      - POSTGRES_USER=odoo
    volumes:
      - ./postgres_data:/var/lib/postgresql/data
    restart: always
    networks:
      - wuchang_network

networks:
  wuchang_network:
    name: wuchang_isolated_net_18

### /home/taiji_01/Taiji_Hub/Wuchang_Odoo_Core/docker-compose.yml
version: '3.8'

services:
  # -----------------------------------------------------
  # 🗄️ 後勤資料庫 (PostgreSQL 15)
  # -----------------------------------------------------
  db:
    image: postgres:15
    container_name: wuchang_odoo_db
    restart: always  # 💥 關鍵：永不關機，死後自動復活
    environment:
      - POSTGRES_DB=postgres
      - POSTGRES_PASSWORD=wuchang_absolute_secret
      - POSTGRES_USER=odoo
    volumes:
      - wuchang_odoo_pg_data:/var/lib/postgresql/data

  # -----------------------------------------------------
  # 🏢 企業後勤大腦 (Odoo 18)
  # -----------------------------------------------------
  web:
    image: odoo:18.0
    container_name: wuchang_odoo_web
    restart: always  # 💥 關鍵：與資料庫同生共死
    depends_on:
      - db
    ports:
      - "8069:8069"
    environment:
      - HOST=db
      - USER=odoo
      - PASSWORD=wuchang_absolute_secret
    volumes:
      - wuchang_odoo_web_data:/var/lib/odoo

# 宣告實體固化硬碟 (確保資料重開機不見)
volumes:
  wuchang_odoo_pg_data:
  wuchang_odoo_web_data:

### /home/taiji_01/Taiji_Hub/Taiji_Odoo/docker-compose.yml
version: '3.1'
services:
  web:
    image: odoo:18.0
    container_name: wuchang_os_odoo_18
    depends_on:
      - db
    ports:
      - "8069:8069"
    volumes:
      - ./addons:/mnt/extra-addons
      - ./odoo_data:/var/lib/odoo
    environment:
      - HOST=db
      - USER=odoo
      - PASSWORD=taiji_secret
    restart: always

  db:
    image: postgres:15
    container_name: wuchang_os_pg
    environment:
      - POSTGRES_DB=postgres
      - POSTGRES_PASSWORD=taiji_secret
      - POSTGRES_USER=odoo
    volumes:
      - odoo-db-data:/var/lib/postgresql/data
    restart: always

volumes:
  odoo-db-data:
    external: true
    name: taiji_odoo_odoo-db-data

### /home/taiji_01/wuchang_node/Taiji_Hub/Taiji_Odoo/docker-compose.yml
version: '3.1'
services:
  web:
    image: odoo:18.0
    container_name: wuchang_os_odoo_18
    depends_on:
      - db
    ports:
      - "8069:8069"
    volumes:
      - ./addons:/mnt/extra-addons
      - ./odoo_data:/var/lib/odoo
    environment:
      - HOST=db
      - USER=odoo
      - PASSWORD=taiji_secret
    restart: always

  db:
    image: postgres:15
    container_name: wuchang_os_pg
    environment:
      - POSTGRES_DB=postgres
      - POSTGRES_PASSWORD=taiji_secret
      - POSTGRES_USER=odoo
    volumes:
      - ./postgres_data:/var/lib/postgresql/data
    restart: always

## oauth/google/line module presence by candidate

### /home/taiji_admin/Taiji_Hub_Community/Taiji_Odoo
0

### /home/taiji_admin/Taiji_Hub_Coffee/Taiji_Odoo
0

### /home/taiji_01/Taiji_Hub/Wuchang_Odoo_Core
0

### /home/taiji_01/Taiji_Hub/Taiji_Odoo
31

### /home/taiji_01/wuchang_node/Taiji_Hub/Taiji_Odoo
4
