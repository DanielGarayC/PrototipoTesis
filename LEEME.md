# NiFi: dependencias incorporadas y reutilizacion de almacenamiento

Este paquete SUSTITUYE las instrucciones del ZIP NiFi_Despliegue_PF06.
Preparado para el inventario proporcionado por el usuario, proyecto prototipotesis,
carpeta C:\Users\Daniel\Desktop\Uni\PrototipoTesis\Docker\PrototipoTesis.
No se ha aplicado ningun cambio en la PC del usuario.

## Objetivo y alcance

Crear NiFi 2.7.2 con el entorno de conversion y volver a conectar su configuracion,
repositorios, extensiones, logs y estado actuales. No reconstruir los procesadores
ni copiar archivos pendientes a mano. Cada volumen existente se declara external
con su identificador EXACTO, obtenido de docker inspect.
Los nombres nifi_content, etc. son alias en Compose: no renombran ni vacian volumenes.
La imagen y el almacenamiento son piezas separadas.

## 1. Copiar archivos sin reemplazar todavia el Compose

Extraer el ZIP aparte. Copiar nifi-image, docker-compose.propuesto.yml y
Respaldar-NiFi.ps1 junto al docker-compose.yml vigente. Abrir PowerShell alli.
Conservar las carpetas central, mysql, data, scripts y nifi-conf.

## 2. Construir mientras el contenedor viejo sigue disponible

```powershell
docker build -t tesis/nifi:2.7.2-pf06 ./nifi-image
```

La imagen instala las seis versiones comunicadas por pip freeze, ejecuta pip check
y comprueba importaciones. Las versiones se conservan como evidencia proporcionada;
su disponibilidad se comprobara en la construccion real. Si hay error, no continuar.
No se arranca otra instancia NiFi durante build ni se reemplaza la existente.
El entorno se usa llamando /opt/nifi/venvs/conversion/bin/python; no hay activate
ni un contenedor adicional. Reiniciar Docker no requiere activar ese entorno.

## 3. Preparar la credencial y validar la configuracion propuesta

Editar el .env existente y AGREGAR (sin borrar las claves MySQL) esta variable:

```dotenv
TESIS_NIFI_PASSWORD='TU_CONTRASENA_ACTUAL_DE_NIFI'
```

Sustituir el texto de ejemplo localmente por la contrasena actual, no una nueva.
Las comillas simples evitan interpolar $ y #. Si la contrasena contiene una comilla
simple, no copiar el ejemplo literalmente: revisar el escape de .env antes de usarlo.
No enviar .env ni respaldos con secretos al chat o a repositorios publicos.
El usuario admin se mantiene como en el Compose recibido.

```powershell
docker compose -f docker-compose.propuesto.yml config --quiet
```

-f selecciona el archivo propuesto solo para esta comprobacion; --quiet valida
sin imprimir la configuracion ni contrasenas. La validacion no crea contenedores
ni demuestra que las bibliotecas o los volumenes funcionen. Si falla, detenerse.

## 4. Detener componentes y respaldar

En la interfaz NiFi detener los grupos/procesadores y puertos de este prototipo.
Esperar a que las tareas activas lleguen a cero. No vaciar colas. Anotar o capturar
grupos y cantidad de archivos pendientes para comparar despues.

```powershell
docker stop -t 120 nifi_tesis
```

Solicita parada y permite hasta 120 segundos antes de forzarla. Si fuerza cierre
o hay error, no avanzar hasta comprobar un cierre limpio.

```powershell
.\Respaldar-NiFi.ps1
```

El script exige contenedor detenido, verifica los ocho identificadores y conf,
copia conf y repositorios al host, scripts, Compose y .env, y comprueba el codigo
de cada docker cp. No elimina datos. Detiene el proceso ante un fallo. Usa una
carpeta nueva con fecha en respaldos. Debe imprimir RESPALDO_COMPLETADO.
Puede requerir espacio considerable: contenido y procedencia pueden crecer.
Si PowerShell bloquea el script por una politica, compartir el mensaje; no cambiar
politicas de equipo a ciegas. Si falla el respaldo no recrear el contenedor.

Es una copia del almacenamiento NiFi indicado, no un backup integral de la plataforma.
No incluye carpeta data, MySQL ni AWS. No se ha ensayado restauracion. Docker cp a
Windows puede no conservar todos los metadatos POSIX: una restauracion posterior
requiere revisar permisos/propietarios. En este cambio se REUTILIZAN los volumenes
originales Linux; no se restaura desde esas copias ni se modifican sus permisos.
Si tienes repositorios personalizados fuera de las ubicaciones del inventario,
tambien deben respaldarse antes de continuar.

## 5. Aplicar el unico Compose y recrear solo NiFi

Solo cuando build y respaldo hayan terminado correctamente:

```powershell
Copy-Item .\docker-compose.propuesto.yml .\docker-compose.yml
docker compose config --quiet
```

Son dos comandos separados. Si la validacion falla no ejecutar el siguiente.
El Compose anterior queda en la carpeta del respaldo. Se fija name: prototipotesis
para conservar identidad del proyecto y mysql_data. La URL de healthcheck central
se corrige a texto plano; ese servicio no se recrea en este procedimiento.

```powershell
docker compose up -d --no-deps --no-build nifi
```

Recrea nifi usando la imagen construida y los volumenes existentes. -d lo deja en
segundo plano; --no-deps no inicia/recrea servicios dependientes; --no-build utiliza
la imagen ya comprobada; nifi limita la operacion a ese servicio.
No ejecutar down, down -v, renew-anon-volumes, prune ni borrar los volumenes.
No editar ni regenerar nifi-conf: contiene flujo, certificados y claves necesarias.

## 6. Comprobar el resultado

```powershell
docker compose ps
docker exec nifi_tesis /opt/nifi/venvs/conversion/bin/python -c "import dwdatareader, numpy, pandas; print('IMPORTACION_OK')"
```

Abrir https://localhost:8443/nifi/ cuando NiFi termine de iniciar. Comprobar:
- Mismos grupos, procesadores, conexiones y parametros.
- Mismas colas pendientes que antes del cierre (componentes siguen detenidos).
- Conversion apunta al Python /opt/nifi/venvs/conversion/bin/python.
- Montajes siguen usando los identificadores declarados (consultar inspect).
- TXT de PF-06 permanece en data; no es necesario reconvertirlo para demostrar
  que se conservo el almacenamiento.

Si el arranque falla: no vaciar colas ni reemplazar conf. Revisar localmente los
ultimos logs y compartir solamente el error relevante, ocultando credenciales.
El contenedor viejo ya habra sido sustituido; los volumenes y respaldo permanecen.
La recuperacion debe atender al error observado, no borrar y crear otra vez todo.

## Portabilidad a otra PC

Los IDs external de este archivo son de ESTA instalacion. En otra PC no existiran
automaticamente. Alli hay que restaurar/configurar volumenes y adecuar name: de
cada volumen; copiar tambien data, scripts, conf, central y respaldar/restaurar
MySQL, ademas de proporcionar credenciales. El ZIP no es un clon de la plataforma.

## Evidencia y limites de verificacion

PF-06: usuario reporto 124006 filas, cinco columnas visibles, TXT presente y codigo
0 del conversor. Compatibilidad efectiva con LabVIEW pendiente.
Este paquete: YAML analizado, hashes de volumenes cotejados contra el inventario,
ZIP comprobado y scripts revisados. No se ejecuto Docker ni PowerShell en el
entorno de preparacion. Su funcionamiento final se comprobara en la PC del usuario.
No cambiar el alcance de los capitulos 1-3 ni presentar el empaquetado como
evidencia de escalabilidad o alta disponibilidad.
