.PHONY: run db cert clean

run: capture_plugin.so instance
	venv/bin/uwsgi --master --http 0.0.0.0:5000 --http-websockets --wsgi basket.run:app --processes 4 --threads 2 \
	--mule=basket.worker:$(shell (command -v bluetoothctl > /dev/null && echo run_worker) || echo run_dummy_worker) \
	$(shell [ -e /dev/video0 ] && echo --plugin capture --v4l-device /dev/video0 || true)

capture_plugin.so: venv
	rm -rf uwsgi-capture
	curl -L https://api.github.com/repos/milkey-mouse/uwsgi-capture/tarball/master | tar -zx
	mv *-uwsgi-capture-* uwsgi-capture
	cd uwsgi-capture && ../venv/bin/uwsgi --build-plugin . && cp *.so ..

instance: venv
	mkdir -p instance
        ifeq (,$(wildcard instance/basket.sqlite))
		FLASK_APP=basket venv/bin/flask init-db
        endif

venv:
	python3 -m venv venv --system-site-packages
	venv/bin/python3 -m pip install -Ur requirements.txt
	# only install bluetooth stuff if bluez userland tools are already installed
	(command -v bluetoothctl > /dev/null && venv/bin/python3 -m pip install -Ur requirements.d/bluetooth.txt) || true

cert: instance
	openssl req -x509 -nodes -sha256 -days 365 -newkey rsa:4096 -keyout instance/self-signed.key -out instance/self-signed.crt -subj "/CN=`hostname`"

clean:
	rm -rf venv instance uwsgi-capture capture_plugin.so
