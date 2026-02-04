-- Database Structure Backup
-- Generated on: 04-02-2026 19:54

DROP TABLE IF EXISTS "favorites" CASCADE;
CREATE TABLE favorites (
	id SERIAL NOT NULL, 
	symbol VARCHAR, 
	current_value DOUBLE PRECISION, 
	alert_value DOUBLE PRECISION, 
	alert_direction VARCHAR, 
	timestamp TIMESTAMP WITHOUT TIME ZONE, 
	CONSTRAINT favorites_pkey PRIMARY KEY (id)
);

DROP TABLE IF EXISTS "rsi_1d" CASCADE;
CREATE TABLE rsi_1d (
	id SERIAL NOT NULL, 
	symbol VARCHAR, 
	rsi_value DOUBLE PRECISION, 
	variation DOUBLE PRECISION, 
	rvol_1 DOUBLE PRECISION, 
	rvol_2 DOUBLE PRECISION, 
	promedio_variacion_3m DOUBLE PRECISION, 
	valor_actual DOUBLE PRECISION, 
	min_price DOUBLE PRECISION, 
	candles_since_min INTEGER, 
	entry_date TIMESTAMP WITHOUT TIME ZONE, 
	timestamp TIMESTAMP WITHOUT TIME ZONE, 
	CONSTRAINT rsi_1d_pkey PRIMARY KEY (id)
);

DROP TABLE IF EXISTS "rsi_4h" CASCADE;
CREATE TABLE rsi_4h (
	id SERIAL NOT NULL, 
	symbol VARCHAR, 
	rsi_value DOUBLE PRECISION, 
	variation DOUBLE PRECISION, 
	rvol_1 DOUBLE PRECISION, 
	rvol_2 DOUBLE PRECISION, 
	timestamp TIMESTAMP WITHOUT TIME ZONE, 
	CONSTRAINT rsi_4h_pkey PRIMARY KEY (id)
);

DROP TABLE IF EXISTS "stock_list" CASCADE;
CREATE TABLE stock_list (
	id SERIAL NOT NULL, 
	symbol VARCHAR, 
	CONSTRAINT stock_list_pkey PRIMARY KEY (id)
);

DROP TABLE IF EXISTS "stock_tracking" CASCADE;
CREATE TABLE stock_tracking (
	id SERIAL NOT NULL, 
	symbol VARCHAR, 
	current_price DOUBLE PRECISION, 
	rsi_value DOUBLE PRECISION, 
	variation DOUBLE PRECISION, 
	rvol_1 DOUBLE PRECISION, 
	rvol_2 DOUBLE PRECISION, 
	hma_a DOUBLE PRECISION, 
	hma_b DOUBLE PRECISION, 
	rsi_limit DOUBLE PRECISION, 
	estado VARCHAR, 
	timestamp TIMESTAMP WITHOUT TIME ZONE, 
	CONSTRAINT stock_tracking_pkey PRIMARY KEY (id)
);

