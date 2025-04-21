según veo
iframe title = Verification challenge con este src https://client-api.arkoselabs.com/v2/3.2.0/enforcement.89e741358ad1db012c73c4b8c1a38f62.html#2F4F0B28-BC94-4271-8AD7-A51662E3C91C&fa6d7cf5-f7fd-4e8a-9ca7-636ebb9c44fa

con un body y dentro un dv id="app" dentro de ese div hay otro div id=challenge y dentro otro div con id=funcaptcha

dentro de ese div está otro iframe title y aria-label "Desafío visual"
con este src https://client-api.arkoselabs.com/fc/assets/ec-game-core/game-core/1.27.4/standard/index.html?session=64018386bcd5ac3a3.3916971801&r=us-east-1&meta=3&meta_width=558&meta_height=523&metabgclr=transparent&metaiconclr=%23555555&guitextcolor=%23000000&pk=2F4F0B28-BC94-4271-8AD7-A51662E3C91C&at=40&ag=101&cdn_url=https%3A%2F%2Fclient-api.arkoselabs.com%2Fcdn%2Ffc&surl=https%3A%2F%2Fclient-api.arkoselabs.com&smurl=https%3A%2F%2Fclient-api.arkoselabs.com%2Fcdn%2Ffc%2Fassets%2Fstyle-manager&theme=dark

dentro de ese iframe tenemos el body con un div id=root lang es-ES

tiene este h2 <h2 font-size="1.5" tabindex="-1" data-theme="home.title" class="sc-1io4bok-0 gdVRUf heading text">Autentifica tu cuenta</h2>

y en ese html aparece el botón:

<button class="sc-nkuzb1-0 sc-d5trka-0 eZxMRy button" data-theme="home.verifyButton">Autentificar</button>

necesitamos un script que siga todo el proceso de corre, siguiente, 3 segundos de carga, e intente extraer todo ese html de dentro de los iframes. Creo que una vez veamos esos iframes estaremos más cerca de poder hacer  click en el botón Autentificar, correcto?