USE lighting_db;

CREATE TABLE modes (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  name VARCHAR(64) NOT NULL,
  PRIMARY KEY (id)
);

CREATE TABLE patterns (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  name VARCHAR(64) NOT NULL,
  num_colors INT UNSIGNED NOT NULL DEFAULT 0,
  PRIMARY KEY (id)
);

CREATE TABLE lightsticks (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  is_on BOOLEAN NOT NULL DEFAULT true,
  mode INT UNSIGNED NOT NULL DEFAULT 1,
  pattern INT UNSIGNED NOT NULL DEFAULT 1,
  colors VARCHAR(256),
  PRIMARY KEY (id),
  FOREIGN KEY (mode) REFERENCES modes(id),
  FOREIGN KEY (pattern) REFERENCES patterns(id)
);

INSERT INTO modes (name) VALUES ('basic');
INSERT INTO modes (name) VALUES ('image');
INSERT INTO modes (name) VALUES ('audio');
INSERT INTO modes (name) VALUES ('microphone');
INSERT INTO modes (name) VALUES ('lightsaber');

INSERT INTO patterns (name, num_colors) VALUES ('solid', 1);
INSERT INTO patterns (name, num_colors) VALUES ('dot', 1);
INSERT INTO patterns (name, num_colors) VALUES ('blink', 1);
INSERT INTO patterns (name, num_colors) VALUES ('breathe', 1);
INSERT INTO patterns (name, num_colors) VALUES ('rainbow', 0);
INSERT INTO patterns (name, num_colors) VALUES ('wave', 2);

INSERT INTO lightsticks () VALUES ();
