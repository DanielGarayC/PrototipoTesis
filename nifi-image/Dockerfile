FROM apache/nifi:2.7.2

# La imagen oficial de esta version ya incluye python3 y python3-venv.
# El entorno se construye en la imagen: no es otro servicio ni contenedor.
USER nifi
COPY requirements-conversion.txt /opt/nifi/requirements-conversion.txt

RUN python3 -m venv /opt/nifi/venvs/conversion \
    && /opt/nifi/venvs/conversion/bin/python -m pip install --no-cache-dir -r /opt/nifi/requirements-conversion.txt \
    && /opt/nifi/venvs/conversion/bin/python -m pip check \
    && /opt/nifi/venvs/conversion/bin/python -c "import dwdatareader, numpy, pandas; print('IMPORTACION_OK')"

# Se heredan ENTRYPOINT, puertos y directorios de NiFi.
# No se copian credenciales, datos, scripts ni configuracion del prototipo.
