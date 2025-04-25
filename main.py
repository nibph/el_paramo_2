import pygame
import random
import os
import math
import cProfile
import pygame.gfxdraw
from pygame import Surface, SRCALPHA
from typing import List, Dict, Tuple
import numpy as np
import asyncio

# ============= INICIALIZACIÓN Y CONFIGURACIÓN =============
pygame.init()
pygame.font.init()

# Definición de colores básicos
NEGRO = (0, 0, 0)
BLANCO = (255, 255, 255)
ROJO = (255, 0, 0)
VERDE = (0, 255, 0)
AZUL = (0, 0, 255)
AMARILLO = (255, 255, 0)
GRIS = (128, 128, 128)
GRIS_OSCURO = (50, 50, 50)
NARANJA = (255, 165, 0)
# Configuración de fuentes
try:
    FUENTE_TITULO = pygame.font.Font("fonts/MedievalSharp-Regular.ttf", 74)
    FUENTE_BOTONES = pygame.font.Font("fonts/MedievalSharp-Regular.ttf", 36)
    FUENTE_NORMAL = pygame.font.Font("fonts/MedievalSharp-Regular.ttf", 30)
except:
    print("⚠️ No se pudieron cargar las fuentes personalizadas. Usando fuentes por defecto.")
    FUENTE_TITULO = pygame.font.Font(None, 74)
    FUENTE_BOTONES = pygame.font.Font(None, 36)
    FUENTE_NORMAL = pygame.font.Font(None, 30)

# Colores mejorados
DORADO = (218, 165, 32)
DORADO_CLARO = (255, 215, 0)
MARRON_OSCURO = (72, 60, 50)
MARRON_CLARO = (139, 69, 19)
CREMA = (255, 248, 220)

# Configuración de la pantalla y juego
ANCHO = 800
ALTO = 600
TITULO = "El Páramo"
FPS = 60
TAMAÑO_PERSONAJE = 80
TAMAÑO_ATAQUE = 30
TAMAÑO_ITEM = 30

# Configuración de gameplay
DELAY_ATAQUE_NORMAL = 300
DELAY_ATAQUE_ENEMIGO = 2000
TIEMPO_INVULNERABLE = 1000
ENERGIA_INICIAL = 50
COSTO_ENERGIA_SPRINT = 2  # Duplicado de 1 a 2
MAX_POSICIONES_SPRINT = 10
TIEMPO_RECARGA_TOTAL = 5000  # 5 segundos para recargar completamente

# Delays para items
DELAY_ITEM_VIDA = 15000
DELAY_ITEM_ENERGIA = 6000  # Reducido de 12000 a 6000 para mayor frecuencia
DELAY_ITEM_SORPRESA = 25000

# Configuración de pantalla
pantalla = pygame.display.set_mode((ANCHO, ALTO), pygame.DOUBLEBUF)
pygame.display.set_caption(TITULO)
reloj = pygame.time.Clock()
fuente = pygame.font.Font(None, 30)

# Cargar sonidos (con manejo de errores)
try:
    sonido_ataque = pygame.mixer.Sound("sounds/attack.wav")
    sonido_golpe = pygame.mixer.Sound("sounds/hit.wav")
except:
    print("⚠️ Error al cargar sonidos. El juego continuará sin efectos de sonido.")
    sonido_ataque = sonido_golpe = type('DummySound', (), {'play': lambda: None})()

# Cache de imágenes y superficies
cache_imagenes: Dict[str, Surface] = {}
cache_rotaciones: Dict[Tuple[int, float], Surface] = {}

# Cargar y configurar el fondo
try:
    fondo = pygame.image.load("images/fondo.png").convert()
except:
    print("Error cargando fondo")
    fondo = None

# Función para dibujar sombra
def dibujar_sombra(pantalla, x, y, ancho, alto, alpha=128):
    sombra = pygame.Surface((ancho, alto//2), pygame.SRCALPHA)
    pygame.draw.ellipse(sombra, (0, 0, 0, alpha), (0, 0, ancho, alto//2))
    pantalla.blit(sombra, (x, y + alto - alto//4))

class GestorImagenes:
    """Clase para gestionar la carga y cache de imágenes"""
    @staticmethod
    def cargar_imagen(ruta: str, tamaño: Tuple[int, int], color_fallback=None) -> Surface:
        """Carga una imagen con manejo de errores y cache"""
        if ruta not in cache_imagenes:
            try:
                imagen = pygame.image.load(ruta).convert_alpha()
                cache_imagenes[ruta] = pygame.transform.scale(imagen, tamaño)
            except Exception as e:
                print(f"⚠️ Error al cargar {ruta}: {e}")
                superficie = Surface(tamaño, SRCALPHA)
                if color_fallback:
                    superficie.fill(color_fallback)
                cache_imagenes[ruta] = superficie
        return cache_imagenes[ruta]

    @staticmethod
    def rotar_imagen(imagen: Surface, angulo: float) -> Surface:
        """Rota una imagen con cache"""
        clave = (id(imagen), angulo)
        if clave not in cache_rotaciones:
            cache_rotaciones[clave] = pygame.transform.rotate(imagen, angulo)
        return cache_rotaciones[clave]

    @staticmethod
    def crear_superficie_color(tamaño: Tuple[int, int], color: Tuple[int, int, int], alpha: int = 255) -> Surface:
        """Crea una superficie con un color específico"""
        superficie = Surface(tamaño, SRCALPHA)
        color_con_alpha = (*color, alpha)
        superficie.fill(color_con_alpha)
        return superficie

def detectar_colision_circular(x1, y1, r1, x2, y2, r2):
    """Función de utilidad para detectar colisiones usando círculos"""
    dx = x1 - x2
    dy = y1 - y2
    distancia = (dx * dx + dy * dy) ** 0.5
    return distancia < (r1 + r2)

def mantener_en_pantalla(x, y, ancho, alto):
    """Función de utilidad para mantener objetos dentro de la pantalla"""
    x = max(0, min(ANCHO - ancho, x))
    y = max(0, min(ALTO - alto, y))
    return x, y

# ============= CLASES DE ATAQUES =============
class AtaqueEspecial:
    """Clase para los ataques especiales que persiguen al objetivo"""
    def __init__(self, x, y, objetivo):
        self.x = x
        self.y = y
        self.velocidad = 3
        self.objetivo = objetivo
        self.tiempo_creacion = pygame.time.get_ticks()
        self.duracion = 3000
        self.radio = 15
        try:
            self.imagen = pygame.image.load("images/fuego_especial.png")
            self.imagen = pygame.transform.scale(self.imagen, (30, 30))
        except:
            self.imagen = pygame.Surface((30, 30), pygame.SRCALPHA)
            pygame.draw.circle(self.imagen, (255, 200, 0), (15, 15), 15)

    def ha_expirado(self):
        """Verifica si el ataque ha superado su tiempo de vida"""
        return pygame.time.get_ticks() - self.tiempo_creacion > self.duracion

    def mover(self):
        """Mueve el ataque hacia el objetivo"""
        dx = self.objetivo.x + self.objetivo.ancho/2 - self.x
        dy = self.objetivo.y + self.objetivo.alto/2 - self.y
        distancia = max(1, (dx**2 + dy**2)**0.5)
        self.x += (dx / distancia) * self.velocidad
        self.y += (dy / distancia) * self.velocidad

    def dibujar(self, pantalla):
        """Dibuja el ataque hacia el objetivo"""
        pantalla.blit(self.imagen, (self.x, self.y))

    def colisiona_con_jugador(self, jugador):
        """Detecta colisión con el jugador usando círculos"""
        return detectar_colision_circular(
            self.x + self.radio, 
            self.y + self.radio, 
            self.radio,
            jugador.x + jugador.ancho/2, 
            jugador.y + jugador.alto/2, 
            min(jugador.ancho, jugador.alto) / 2.5
        )

class AtaqueFuego:
    """Clase para los ataques de fuego en línea recta"""
    def __init__(self, x, y, direccion):
        self.x = x
        self.y = y
        self.direccion = direccion
        self.velocidad = 4
        try:
            self.imagen = pygame.image.load("images/fuego.png")
            self.imagen = pygame.transform.scale(self.imagen, (20, 20))
        except:
            self.imagen = pygame.Surface((20, 20), pygame.SRCALPHA)
            pygame.draw.circle(self.imagen, (255, 50, 0), (10, 10), 10)  # Rojo más brillante

    def mover(self):
        """Mueve el ataque en la dirección especificada"""
        velocidad_diagonal = self.velocidad * 0.7071  # Ajuste para movimiento diagonal (1/√2)
        
        movimientos = {
            "izquierda": (-self.velocidad, 0),
            "derecha": (self.velocidad, 0),
            "arriba": (0, -self.velocidad),
            "abajo": (0, self.velocidad),
            "arriba-derecha": (velocidad_diagonal, -velocidad_diagonal),
            "arriba-izquierda": (-velocidad_diagonal, -velocidad_diagonal),
            "abajo-derecha": (velocidad_diagonal, velocidad_diagonal),
            "abajo-izquierda": (-velocidad_diagonal, velocidad_diagonal)
        }
        
        dx, dy = movimientos.get(self.direccion, (0, 0))
        self.x += dx
        self.y += dy

    def dibujar(self, pantalla):
        """Dibuja el ataque con la rotación correcta"""
        rotaciones = {
            "izquierda": 180,
            "derecha": 0,
            "arriba": 90,
            "abajo": -90,
            "arriba-derecha": 45,
            "arriba-izquierda": 135,
            "abajo-derecha": -45,
            "abajo-izquierda": -135
        }
        
        angulo = rotaciones.get(self.direccion, 0)
        imagen_rotada = pygame.transform.rotate(self.imagen, angulo)
        pantalla.blit(imagen_rotada, (self.x, self.y))

class AtaqueRayo:
    """Clase para los ataques de rayo del oso"""
    def __init__(self, x, y, direccion, es_especial=False):
        self.x = x
        self.y = y
        self.direccion = direccion
        self.velocidad = 6 if not es_especial else 8  # Ataque especial más rápido
        self.es_especial = es_especial
        try:
            ruta = "images/rayo_especial.png" if es_especial else "images/rayo.png"
            tamaño = (50, 50) if es_especial else (30, 30)
            self.imagen = GestorImagenes.cargar_imagen(ruta, tamaño)
        except Exception as e:
            print(f"Error al cargar imagen de rayo: {e}")
            color = AMARILLO if es_especial else (255, 255, 0)  # Amarillo para los rayos
            self.imagen = self._crear_imagen_fallback(color, es_especial)

    def _crear_imagen_fallback(self, color, es_especial):
        if es_especial:
            imagen = pygame.Surface((50, 50), pygame.SRCALPHA)
            # Rayo especial más elaborado
            pygame.draw.polygon(imagen, color, [
                (25,0), (50,25), (35,25),   # Punta superior
                (50,50), (25,50), (35,25),  # Parte inferior
                (0,25), (15,25)             # Cola
            ])
            # Detalles brillantes
            pygame.draw.line(imagen, BLANCO, (20,25), (40,25), 3)
        else:
            imagen = pygame.Surface((30, 30), pygame.SRCALPHA)
            # Rayo normal más simple
            pygame.draw.polygon(imagen, color, [(15,0), (30,15), (20,15), (30,30), (0,15), (10,15)])
        return imagen

    def mover(self):
        """Mueve el rayo en la dirección especificada, incluyendo diagonales"""
        velocidad_diagonal = self.velocidad * 0.7071  # Ajuste para movimiento diagonal (1/√2)
        
        movimientos = {
            "izquierda": (-self.velocidad, 0),
            "derecha": (self.velocidad, 0),
            "arriba": (0, -self.velocidad),
            "abajo": (0, self.velocidad),
            "arriba-derecha": (velocidad_diagonal, -velocidad_diagonal),
            "arriba-izquierda": (-velocidad_diagonal, -velocidad_diagonal),
            "abajo-derecha": (velocidad_diagonal, velocidad_diagonal),
            "abajo-izquierda": (-velocidad_diagonal, velocidad_diagonal)
        }
        
        dx, dy = movimientos.get(self.direccion, (0, 0))
        self.x += dx
        self.y += dy

    def dibujar(self, pantalla):
        """Dibuja el rayo con la rotación correcta, incluyendo diagonales"""
        rotaciones = {
            "izquierda": 180,
            "derecha": 0,
            "arriba": 90,
            "abajo": -90,
            "arriba-derecha": 45,
            "arriba-izquierda": 135,
            "abajo-derecha": -45,
            "abajo-izquierda": -135
        }
        
        angulo = rotaciones.get(self.direccion, 0)
        imagen_rotada = pygame.transform.rotate(self.imagen, angulo)
        pantalla.blit(imagen_rotada, (self.x, self.y))

class Roca:
    """Clase para las rocas que sirven como cobertura"""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.ancho = 80
        self.alto = 80
        self.radio = self.ancho // 2  # Radio para colisiones circulares
        self.centro_x = self.x + self.radio
        self.centro_y = self.y + self.radio
        self.vida = 30  # Vida inicial de la roca
        self.vida_maxima = 30

        # Intentar cargar las imágenes con manejo de errores individual
        try:
            self.imagen_normal = pygame.image.load("images/roca.png")
            self.imagen_normal = pygame.transform.scale(self.imagen_normal, (self.ancho, self.alto))
        except:
            print("⚠️ No se pudo cargar roca.png")
            self.imagen_normal = pygame.Surface((self.ancho, self.alto))
            pygame.draw.circle(self.imagen_normal, (100, 100, 100), (self.radio, self.radio), self.radio)

        try:
            self.imagen_grietas = pygame.image.load("images/roca_grietas.png")
            self.imagen_grietas = pygame.transform.scale(self.imagen_grietas, (self.ancho, self.alto))
        except:
            print("⚠️ No se pudo cargar roca_grietas.png")
            self.imagen_grietas = self.imagen_normal

        try:
            self.imagen_destruida = pygame.image.load("images/roca_destruida.png")
            self.imagen_destruida = pygame.transform.scale(self.imagen_destruida, (self.ancho, self.alto))
        except:
            print("⚠️ No se pudo cargar roca_destruida.png")
            self.imagen_destruida = self.imagen_normal

        self.imagen = self.imagen_normal
        self.destruyendo = False
        self.tiempo_destruccion = None

    def dibujar(self, pantalla):
        """Dibuja la roca con su apariencia según su vida"""
        vida_porcentaje = self.vida / self.vida_maxima
        if vida_porcentaje > 0.5:
            self.imagen = self.imagen_normal
        elif vida_porcentaje > 0.25:
            self.imagen = self.imagen_grietas
        else:
            self.imagen = self.imagen_destruida
        pantalla.blit(self.imagen, (self.x, self.y))

    def recibir_dano(self, dano):
        """Procesa el daño recibido por la roca"""
        self.vida = max(0, self.vida - dano)
        if self.vida <= 0 and not self.destruyendo:
            self.imagen = self.imagen_destruida
            self.destruyendo = True
            self.tiempo_destruccion = pygame.time.get_ticks()
            return False
        elif self.vida <= self.vida_maxima * 0.5:
            self.imagen = self.imagen_grietas
        return False

    def colisiona_con_circulo(self, x1, y1, r1, x2=None, y2=None, r2=None):
        """Detecta colisión usando círculos"""
        if x2 is None and y2 is None and r2 is None:
            # Versión antigua con 3 parámetros
            return detectar_colision_circular(self.centro_x, self.centro_y, self.radio, x1, y1, r1)
        else:
            # Nueva versión con 6 parámetros
            return detectar_colision_circular(x1, y1, r1, x2, y2, r2)

    def actualizar(self):
        """Actualiza el estado de la roca"""
        if self.destruyendo:
            tiempo_actual = pygame.time.get_ticks()
            if tiempo_actual - self.tiempo_destruccion > 500:
                return True
        return False

class ItemVida:
    """Clase para el ítem de vida que aparece aleatoriamente"""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.velocidad = 1.5
        self.tiempo_creacion = pygame.time.get_ticks()
        self.duracion = 10000
        self.angulo = random.uniform(0, 2 * 3.1416)
        self.tiempo_cambio_direccion = pygame.time.get_ticks()
        self.delay_cambio_direccion = 3000
        try:
            self.imagen = pygame.image.load("images/vida.png")
            self.imagen = pygame.transform.scale(self.imagen, (30, 30))
        except:
            self.imagen = pygame.Surface((30, 30), pygame.SRCALPHA)
            pygame.draw.circle(self.imagen, (0, 255, 0), (15, 15), 15)  # Verde brillante
            pygame.draw.circle(self.imagen, (255, 255, 255), (15, 15), 7)  # Centro blanco

    def ha_expirado(self):
        """Verifica si el ítem ha superado su tiempo de vida"""
        return pygame.time.get_ticks() - self.tiempo_creacion > self.duracion

    def mover(self):
        """Mueve el ítem con un movimiento más suave"""
        tiempo_actual = pygame.time.get_ticks()
        
        # Cambiar dirección gradualmente
        if tiempo_actual - self.tiempo_cambio_direccion >= self.delay_cambio_direccion:
            self.angulo = random.uniform(0, 2 * 3.1416)
            self.tiempo_cambio_direccion = tiempo_actual

        # Mover en la dirección del ángulo actual
        self.x += self.velocidad * math.cos(self.angulo)
        self.y += self.velocidad * math.sin(self.angulo)
        
        # Mantener dentro de los límites de la pantalla
        if self.x < 0 or self.x > ANCHO - 30:
            self.angulo = 3.1416 - self.angulo
        if self.y < 0 or self.y > ALTO - 30:
            self.angulo = -self.angulo
            
        self.x, self.y = mantener_en_pantalla(self.x, self.y, 30, 30)

    def dibujar(self, pantalla):
        """Dibuja el ítem en la pantalla"""
        pantalla.blit(self.imagen, (self.x, self.y))

    def colisiona_con_jugador(self, jugador):
        """Detecta si el jugador ha recogido el ítem"""
        return detectar_colision_circular(self.x, self.y, 15, jugador.x, jugador.y, min(jugador.ancho, jugador.alto) / 2.5)

class ItemEnergia:
    """Clase para el ítem de energía que aparece aleatoriamente"""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.velocidad = 1.5
        self.tiempo_creacion = pygame.time.get_ticks()
        self.duracion = 8000
        self.angulo = random.uniform(0, 2 * 3.1416)
        self.tiempo_cambio_direccion = pygame.time.get_ticks()
        self.delay_cambio_direccion = 3000
        try:
            self.imagen = pygame.image.load("images/energia.png")
            self.imagen = pygame.transform.scale(self.imagen, (30, 30))
        except:
            self.imagen = pygame.Surface((30, 30), pygame.SRCALPHA)
            pygame.draw.circle(self.imagen, (255, 255, 0), (15, 15), 15)  # Amarillo brillante
            pygame.draw.polygon(self.imagen, (255, 255, 255), [(15,5), (25,15), (15,25), (5,15)])  # Rayo blanco

    def ha_expirado(self):
        """Verifica si el ítem ha superado su tiempo de vida"""
        return pygame.time.get_ticks() - self.tiempo_creacion > self.duracion

    def mover(self):
        """Mueve el ítem con un movimiento más suave"""
        tiempo_actual = pygame.time.get_ticks()
        
        # Cambiar dirección gradualmente
        if tiempo_actual - self.tiempo_cambio_direccion >= self.delay_cambio_direccion:
            self.angulo = random.uniform(0, 2 * 3.1416)
            self.tiempo_cambio_direccion = tiempo_actual

        # Mover en la dirección del ángulo actual
        self.x += self.velocidad * math.cos(self.angulo)
        self.y += self.velocidad * math.sin(self.angulo)
        
        # Mantener dentro de los límites de la pantalla
        if self.x < 0 or self.x > ANCHO - 30:
            self.angulo = 3.1416 - self.angulo
        if self.y < 0 or self.y > ALTO - 30:
            self.angulo = -self.angulo
            
        self.x, self.y = mantener_en_pantalla(self.x, self.y, 30, 30)

    def dibujar(self, pantalla):
        """Dibuja el ítem en la pantalla"""
        pantalla.blit(self.imagen, (self.x, self.y))

    def colisiona_con_jugador(self, jugador):
        """Detecta si el jugador ha recogido el ítem"""
        return detectar_colision_circular(self.x, self.y, 15, jugador.x, jugador.y, min(jugador.ancho, jugador.alto) / 2.5)

# ============= CLASE PERSONAJE =============
class Personaje:
    """Clase principal para los personajes del juego"""
    def __init__(self, nombre, x, y):
        self.nombre = nombre
        self.vida = 100
        self.vida_maxima = 100
        self.energia = ENERGIA_INICIAL
        self.energia_maxima = ENERGIA_INICIAL
        self.ataque = 20
        self.defensa = 10
        self.velocidad = 5
        self.x = x
        self.y = y
        self.color = (255, 0, 0)  # Rojo
        self.ancho = TAMAÑO_PERSONAJE
        self.alto = TAMAÑO_PERSONAJE
        self.ataques = []
        self.ataques_jugador = []
        self.parpadeo = False
        self.ultimo_golpe = 0
        self.invulnerable = False
        self.mirando_derecha = True
        self.velocidad_actual = self.velocidad
        self.velocidad_base = self.velocidad
        self.sprint_activo = False
        self.posiciones_anteriores = []
        self.max_posiciones = MAX_POSICIONES_SPRINT
        self.ataques_normales_disponibles = 3  # Máximo de ataques normales
        self.ataques_normales_maximos = 3  # Añadir esta línea
        self.tiempo_recarga_ataques = 3000  # segundos de recarga
        self.ultimo_tiempo_recarga = pygame.time.get_ticks()
        self.evolucionado = False
        self.tiempo_evolucion = 0
        self.alpha_evolucion = 0
        self.estado_evolucion = 'normal'
        
        # Nuevos atributos para animación
        self.frame_actual = 0
        self.tiempo_ultimo_frame = pygame.time.get_ticks()
        self.delay_animacion = 150  # Valor base para todas las animaciones
        self.estado_animacion = 'idle'  # idle, walk, attack
        self.sprites = {}
        
        # Cargar sprites
        try:
            # Intentar cargar las hojas de sprites
            if self.nombre == "oso":
                sprite_sheet = pygame.image.load("images/oso_sprites.png").convert_alpha()
                # Primera fila (0): idle
                self.sprites['idle'] = self._cargar_frames(sprite_sheet, 0)
                # Segunda fila (1): walk
                self.sprites['walk'] = self._cargar_frames(sprite_sheet, 1)
                # Tercera fila (2): attack
                self.sprites['attack'] = self._cargar_frames(sprite_sheet, 2)
            elif self.nombre == "puma":
                sprite_sheet = pygame.image.load("images/puma_sprites.png").convert_alpha()
                self.sprites['idle'] = self._cargar_frames(sprite_sheet, 0)
                self.sprites['walk'] = self._cargar_frames(sprite_sheet, 1)
                self.sprites['attack'] = self._cargar_frames(sprite_sheet, 2)
        except Exception as e:
            print(f"Error al cargar sprites para {nombre}: {e}")
            self.imagen = GestorImagenes.crear_superficie_color((self.ancho, self.alto), color)
            self.imagen_original = self.imagen.copy()
            self.sprites = None

        self.tiempo_ultimo_ataque = pygame.time.get_ticks()  # Añadir esta línea
        self.moviendo_x = False
        self.moviendo_y = False
        self.dx_actual = 0
        self.dy_actual = 0
        self.delay_entre_ataques = 200  # 200ms entre cada ataque
        self.ultimo_ataque_normal = pygame.time.get_ticks()
        self.delay_entre_especiales = 1000  # 1000ms (1 segundo) entre ataques especiales
        self.ultimo_ataque_especial = pygame.time.get_ticks()  # Nuevo atributo

    def _cargar_frames(self, sprite_sheet, fila):
        """
        Carga los frames de una fila específica del sprite sheet
        fila: 0 para idle, 1 para walk, 2 para attack
        """
        frames = []
        # Cada sprite sheet tiene 4 columnas (frames) y 3 filas (tipos de animación)
        frame_width = sprite_sheet.get_width() // 4
        frame_height = sprite_sheet.get_height() // 3
        
        for columna in range(4):
            # Crear superficie para el frame individual
            frame = pygame.Surface((frame_width, frame_height), pygame.SRCALPHA)
            # Copiar el área específica del sprite sheet
            frame.blit(sprite_sheet, 
                      (0, 0),  # Posición destino en el frame
                      (columna * frame_width,  # X origen en sprite sheet
                       fila * frame_height,    # Y origen en sprite sheet
                       frame_width,            # Ancho del frame
                       frame_height))          # Alto del frame
            # Escalar al tamaño del personaje
            frame = pygame.transform.scale(frame, (self.ancho, self.alto))
            frames.append(frame)
        return frames

    def actualizar_animacion(self):
        tiempo_actual = pygame.time.get_ticks()

        # Manejo específico para cada personaje
        if self.nombre == "oso":
            # Estado de ataque para el oso
            if self.estado_animacion == 'attack':
                if tiempo_actual - self.tiempo_ultimo_frame > 250:  # Más tiempo para ver la animación
                    self.frame_actual = (self.frame_actual + 1) % len(self.sprites[self.estado_animacion])
                    self.tiempo_ultimo_frame = tiempo_actual
                    # Mantener el ataque por más tiempo
                    if self.frame_actual == len(self.sprites[self.estado_animacion]) - 1:
                        # Esperar un poco más antes de cambiar
                        if tiempo_actual - self.tiempo_ultimo_ataque > 500:  # 500ms de duración total
                            if self.moviendo_x or self.moviendo_y:
                                self.estado_animacion = 'walk'
                            else:
                                self.estado_animacion = 'idle'
                            self.frame_actual = 0
            else:
                # Cambiar entre walk e idle según movimiento
                if self.moviendo_x or self.moviendo_y:
                    self.estado_animacion = 'walk'
                else:
                    self.estado_animacion = 'idle'
                
                if tiempo_actual - self.tiempo_ultimo_frame > self.delay_animacion:
                    self.frame_actual = (self.frame_actual + 1) % len(self.sprites[self.estado_animacion])
                    self.tiempo_ultimo_frame = tiempo_actual

        elif self.nombre == "puma" or self.nombre == "puma2":
            # Estado de ataque para los pumas
            if self.estado_animacion == 'attack':
                if tiempo_actual - self.tiempo_ultimo_frame > 100:
                    self.frame_actual = (self.frame_actual + 1) % len(self.sprites[self.estado_animacion])
                    self.tiempo_ultimo_frame = tiempo_actual
                    # Cambiar a walk después de completar la animación
                    if self.frame_actual == len(self.sprites[self.estado_animacion]) - 1:
                        if self.moviendo_x or self.moviendo_y:
                            self.estado_animacion = 'walk'
                        else:
                            self.estado_animacion = 'idle'
                        self.frame_actual = 0
            else:
                # Actualizar estado según movimiento
                nuevo_estado = 'idle'
                if abs(self.dx_actual) > 0.1 or abs(self.dy_actual) > 0.1:
                    nuevo_estado = 'walk'
                    self.moviendo_x = True
                    self.moviendo_y = True
                else:
                    self.moviendo_x = False
                    self.moviendo_y = False

                if self.estado_animacion != nuevo_estado:
                    self.estado_animacion = nuevo_estado
                    self.frame_actual = 0

                if tiempo_actual - self.tiempo_ultimo_frame > self.delay_animacion:
                    self.frame_actual = (self.frame_actual + 1) % len(self.sprites[self.estado_animacion])
                    self.tiempo_ultimo_frame = tiempo_actual

    def mover_ia(self, rocas, jugador):
        """Sistema de movimiento para el villano"""
        # Actualizar dirección mirando al jugador
        if self.nombre == "puma" or self.nombre == "puma2":  # Añadir puma2
            self.mirando_derecha = self.x < jugador.x

            # Inicializar variables de estado si no existen
            if not hasattr(self, 'estado_movimiento'):
                self.estado_movimiento = 'perseguir'
                self.tiempo_ultimo_cambio = pygame.time.get_ticks()
                self.dx_actual = 0
                self.dy_actual = 0
                self.velocidad_actual = self.velocidad * 0.8
                self.tiempo_ultimo_sprint = pygame.time.get_ticks()
                self.duracion_sprint = 1000
                self.cooldown_sprint = 3000
                self.moviendo_x = False  # Añadir estos atributos
                self.moviendo_y = False  # Añadir estos atributos

            tiempo_actual = pygame.time.get_ticks()

            # Calcular distancia al jugador
            dx = jugador.x - self.x
            dy = jugador.y - self.y
            distancia_al_jugador = (dx * dx + dy * dy) ** 0.5

            # Definir márgenes de seguridad para los bordes
            margen_borde = 100
            cerca_borde_izq = self.x < margen_borde
            cerca_borde_der = self.x > ANCHO - self.ancho - margen_borde
            cerca_borde_sup = self.y < margen_borde
            cerca_borde_inf = self.y > ALTO - self.alto - margen_borde

            # Vector objetivo de movimiento
            dx_objetivo = 0
            dy_objetivo = 0

            # Lógica de estados de movimiento
            if cerca_borde_izq or cerca_borde_der or cerca_borde_sup or cerca_borde_inf:
                # Estado: Alejarse de los bordes
                dx_objetivo = (ANCHO/2 - self.x) / ANCHO
                dy_objetivo = (ALTO/2 - self.y) / ALTO
            elif distancia_al_jugador < 200:
                # Estado: Alejarse del jugador
                dx_objetivo = -dx / distancia_al_jugador
                dy_objetivo = -dy / distancia_al_jugador
            else:
                # Estado: Movimiento semi-aleatorio
                if tiempo_actual - self.tiempo_ultimo_cambio > 2000:
                    self.tiempo_ultimo_cambio = tiempo_actual
                    angulo = random.uniform(0, 2 * math.pi)
                    dx_objetivo = math.cos(angulo)
                    dy_objetivo = math.sin(angulo)
                else:
                    dx_objetivo = self.dx_actual
                    dy_objetivo = self.dy_actual

            # Lógica de sprint
            puede_sprint = tiempo_actual - self.tiempo_ultimo_sprint > self.cooldown_sprint
            distancia_optima_sprint = 300 if self.evolucionado else 400
            
            # Activar sprint si:
            # 1. El puma está evolucionado o hay una probabilidad del 30%
            # 2. La distancia al jugador es óptima
            # 3. Ha pasado el tiempo de cooldown
            # 4. Tiene suficiente energía
            if puede_sprint and self.energia > 20 and (self.evolucionado or random.random() < 0.3):
                if abs(distancia_al_jugador - distancia_optima_sprint) < 100:
                    self.sprint_activo = True
                    self.velocidad_actual = self.velocidad_base * (2 if self.evolucionado else 1.5)
                    self.energia = max(0, self.energia - 1)
                    self.tiempo_ultimo_sprint = tiempo_actual
                else:
                    self.sprint_activo = False
                    self.velocidad_actual = self.velocidad_base
            elif tiempo_actual - self.tiempo_ultimo_sprint > self.duracion_sprint:
                self.sprint_activo = False
                self.velocidad_actual = self.velocidad_base

            # Normalizar vector objetivo
            magnitud = math.sqrt(dx_objetivo * dx_objetivo + dy_objetivo * dy_objetivo)
            if magnitud > 0:
                dx_objetivo /= magnitud
                dy_objetivo /= magnitud

            # Aplicar inercia suave
            factor_inercia = 0.1
            self.dx_actual = self.dx_actual * (1 - factor_inercia) + dx_objetivo * factor_inercia
            self.dy_actual = self.dy_actual * (1 - factor_inercia) + dy_objetivo * factor_inercia

            # Aplicar umbral mínimo de movimiento
            umbral_movimiento = 0.05
            if abs(self.dx_actual) < umbral_movimiento and abs(self.dy_actual) < umbral_movimiento:
                self.dx_actual = 0
                self.dy_actual = 0

            # Calcular nueva posición
            nuevo_x = self.x + self.dx_actual * self.velocidad_actual
            nuevo_y = self.y + self.dy_actual * self.velocidad_actual

            # Actualizar estado de movimiento
            self.moviendo_x = abs(self.dx_actual) > 0.01
            self.moviendo_y = abs(self.dy_actual) > 0.01

            # Aplicar la nueva posición
            self.x = max(0, min(ANCHO - self.ancho, nuevo_x))
            self.y = max(0, min(ALTO - self.alto, nuevo_y))

            # Redondear posición solo cuando está completamente quieto
            if self.dx_actual == 0 and self.dy_actual == 0:
                self.x = round(self.x)
                self.y = round(self.y)

            # Guardar posición para estela de sprint
            if self.sprint_activo:
                if not hasattr(self, 'posiciones_anteriores'):
                    self.posiciones_anteriores = []
                self.posiciones_anteriores.append((self.x, self.y))
                if len(self.posiciones_anteriores) > MAX_POSICIONES_SPRINT:
                    self.posiciones_anteriores.pop(0)

        # Sistema de empuje para colisiones con rocas
        centro_x = self.x + self.ancho/2
        centro_y = self.y + self.alto/2
        radio = min(self.ancho, self.alto) / 2.5

        for roca in rocas:
            if roca.colisiona_con_circulo(centro_x, centro_y, radio):
                # Calcular vector de empuje
                dx_empuje = centro_x - roca.centro_x
                dy_empuje = centro_y - roca.centro_y
                distancia = max(1, math.sqrt(dx_empuje * dx_empuje + dy_empuje * dy_empuje))
                
                # Aplicar empuje más suave
                fuerza_empuje = 2.0
                self.x += (dx_empuje / distancia) * fuerza_empuje
                self.y += (dy_empuje / distancia) * fuerza_empuje
                
                # Reducir la velocidad actual para evitar "rebotes"
                self.dx_actual *= 0.5
                self.dy_actual *= 0.5

        # Asegurar límites de pantalla
        self.x = max(0, min(ANCHO - self.ancho, self.x))
        self.y = max(0, min(ALTO - self.alto, self.y))
    
    def atacar(self, objetivo):
        """Realiza un ataque al objetivo"""
        if not objetivo.invulnerable:
            sonido_ataque.play()
            dano = max(0, self.ataque - objetivo.defensa) 
            objetivo.vida = max(0, objetivo.vida - dano)
            objetivo.recibir_dano()
            print(f"{self.nombre} ataca a {objetivo.nombre} causando {dano} de daño.")
    
    def recibir_dano(self):
        """Procesa la recepción de daño y activa la invulnerabilidad temporal"""
        if not self.invulnerable:
            sonido_golpe.play()
            self.ultimo_golpe = pygame.time.get_ticks()
            self.parpadeo = True
            self.invulnerable = True

    def actualizar_estado(self, tiempo_actual):
        """Actualiza el estado del personaje (invulnerabilidad, parpadeo, etc)"""
        if self.invulnerable and tiempo_actual - self.ultimo_golpe >= TIEMPO_INVULNERABLE:
            self.invulnerable = False
            self.parpadeo = False

    def evolucionar(self):
        """Evoluciona al personaje mejorando sus estadísticas"""
        if self.nombre == "puma" and not self.evolucionado:
            self.evolucionado = True
            self.estado_evolucion = 'evolucionando'
            self.tiempo_evolucion = pygame.time.get_ticks()
            self.vida_maxima *= 2  # Duplicar vida máxima
            self.vida = self.vida_maxima  # Establecer vida actual al nuevo máximo
            self.velocidad *= 1.3  # 30% más rápido
            self.velocidad_base *= 1.3
            self.ataque *= 1.5  # 50% más daño
            
            # Cargar nuevos sprites para el puma evolucionado
            try:
                sprite_sheet = pygame.image.load("images/puma2_sprites.png").convert_alpha()
                # Primera fila (0): idle
                self.sprites['idle'] = self._cargar_frames(sprite_sheet, 0)
                # Segunda fila (1): walk
                self.sprites['walk'] = self._cargar_frames(sprite_sheet, 1)
                # Tercera fila (2): attack
                self.sprites['attack'] = self._cargar_frames(sprite_sheet, 2)
            except Exception as e:
                print(f"Error al cargar sprites de evolución del puma: {e}")
                # Si falla la carga de sprites, crear una versión más brillante del color actual
                color_evolucion = tuple(min(255, c + 50) for c in self.color)
                self.imagen = GestorImagenes.crear_superficie_color(
                    (self.ancho, self.alto),
                    color_evolucion
                )
                self.imagen_original = self.imagen.copy()
            
            self._imagen_cache = {}  # Resetear el caché de imágenes
    
    def dibujar(self, pantalla):
        tiempo_actual = pygame.time.get_ticks()
        self.actualizar_estado(tiempo_actual)
        self.actualizar_animacion()

        if self.sprint_activo and self.nombre == "oso":
            self._dibujar_estela_sprint(pantalla)
        
        if self.parpadeo and (tiempo_actual // 100) % 2 == 0:
            return

        # Animación de evolución
        if self.estado_evolucion == 'evolucionando':
            tiempo_transcurrido = tiempo_actual - self.tiempo_evolucion
            if tiempo_transcurrido < 2000:
                superficie_brillo = Surface((self.ancho + 40, self.alto + 40), SRCALPHA)
                alpha = int(255 * (1 + math.sin(tiempo_transcurrido * 0.01)) / 2)
                color_brillo = (255, 255, 200, alpha)
                pygame.draw.circle(superficie_brillo, color_brillo, 
                                 (self.ancho//2 + 20, self.alto//2 + 20), 
                                 self.ancho//2 + 10)
                pantalla.blit(superficie_brillo, (self.x - 20, self.y - 20))
            else:
                self.estado_evolucion = 'evolucionado'

        # Dibujar sprite actual
        if self.sprites:
            frame = self.sprites[self.estado_animacion][self.frame_actual]
            if self.mirando_derecha:
                frame = pygame.transform.flip(frame, True, False)
            imagen_a_dibujar = frame
        else:
            if not hasattr(self, '_imagen_cache'):
                self._imagen_cache = {}
            
            clave = ('normal', self.mirando_derecha)
            if clave not in self._imagen_cache:
                if self.mirando_derecha:
                    self._imagen_cache[clave] = pygame.transform.flip(self.imagen, True, False)
                else:
                    self._imagen_cache[clave] = self.imagen
            imagen_a_dibujar = self._imagen_cache[clave]
        
        # Efecto de brillo para evolución
        if self.evolucionado and self.estado_evolucion == 'evolucionado':
            tiempo_transcurrido = tiempo_actual - self.tiempo_evolucion
            alpha = int(50 * (1 + math.sin(tiempo_transcurrido * 0.005)) / 2)
            superficie_brillo = Surface((self.ancho, self.alto), SRCALPHA)
            color_brillo = (255, 255, 200, alpha)
            pygame.draw.circle(superficie_brillo, color_brillo, 
                             (self.ancho//2, self.alto//2), 
                             self.ancho//2)
            pantalla.blit(superficie_brillo, (self.x, self.y))
        
        pantalla.blit(imagen_a_dibujar, (self.x, self.y))

    def _dibujar_estela_sprint(self, pantalla):
        """Método separado para dibujar la estela del sprint"""
        if hasattr(self, 'posiciones_anteriores') and len(self.posiciones_anteriores) > 1:
            for i, (pos_x, pos_y) in enumerate(self.posiciones_anteriores[:-1]):
                alpha = int(100 * (i + 1) / len(self.posiciones_anteriores))
                sprint_surface = Surface((self.ancho, self.alto), SRCALPHA)
                sprint_surface.fill((255, 255, 0, alpha))  # Color amarillo con transparencia
                pantalla.blit(sprint_surface, (pos_x, pos_y))

    def dibujar_barra_vida(self, pantalla):
        """Dibuja la barra de vida con cambio de colores"""
        barra_ancho = 80
        barra_alto = 5
        vida_porcentaje = self.vida / self.vida_maxima
        barra_actual = int(barra_ancho * vida_porcentaje)

        # Color según porcentaje de vida
        if vida_porcentaje > 0.7:
            color_barra = VERDE
        elif vida_porcentaje > 0.3:
            color_barra = AMARILLO
        else:
            color_barra = ROJO

        # Barra de fondo
        pygame.draw.rect(pantalla, GRIS, (self.x, self.y - 20, barra_ancho, barra_alto))
        # Barra de vida actual
        pygame.draw.rect(pantalla, color_barra, (self.x, self.y - 20, barra_actual, barra_alto))

        # Barra de energía
        energia_porcentaje = self.energia / self.energia_maxima
        energia_actual = int(barra_ancho * energia_porcentaje)
        pygame.draw.rect(pantalla, GRIS, (self.x, self.y - 15, barra_ancho, 3))
        pygame.draw.rect(pantalla, AZUL, (self.x, self.y - 15, energia_actual, 3))

        # Barra de ataques normales disponibles
        ataques_porcentaje = self.ataques_normales_disponibles / 5
        ataques_actual = int(barra_ancho * ataques_porcentaje)
        pygame.draw.rect(pantalla, GRIS, (self.x, self.y - 10, barra_ancho, 3))
        pygame.draw.rect(pantalla, (255, 165, 0), (self.x, self.y - 10, ataques_actual, 3))  # Color naranja

    def actualizar_sprint(self, sprint_activado):
        if sprint_activado and self.energia > 0:
            self.sprint_activo = True
            self.velocidad_actual = self.velocidad_base * 2
            self.energia = max(0, self.energia - (COSTO_ENERGIA_SPRINT * 2))  # Duplicar el costo
            
            # Guardar la posición actual para la estela
            if not hasattr(self, 'posiciones_anteriores'):
                self.posiciones_anteriores = []
            self.posiciones_anteriores.append((self.x, self.y))
            if len(self.posiciones_anteriores) > self.max_posiciones:
                self.posiciones_anteriores.pop(0)
            
            if self.nombre == "oso":
                self.invulnerable = True
        else:
            self.sprint_activo = False
            self.velocidad_actual = self.velocidad_base
            if hasattr(self, 'posiciones_anteriores'):
                self.posiciones_anteriores.clear()
            if not self.parpadeo:
                self.invulnerable = False

    def actualizar_ataques_normales(self):
        tiempo_actual = pygame.time.get_ticks()
        tiempo_transcurrido = tiempo_actual - self.ultimo_tiempo_recarga
        
        if tiempo_transcurrido >= self.tiempo_recarga_ataques:
            self.ataques_normales_disponibles = 3
            self.ultimo_tiempo_recarga = tiempo_actual

    def atacar_normal(self):
        tiempo_actual = pygame.time.get_ticks()
        if (self.ataques_normales_disponibles > 0 and 
            tiempo_actual - self.ultimo_ataque_normal >= self.delay_entre_ataques):
            self.ataques_normales_disponibles -= 1
            self.ultimo_ataque_normal = tiempo_actual
            return True
        return False

    def dibujar_barra_ataques(self, pantalla):
        if self.ataques_normales_disponibles < 3:
            tiempo_actual = pygame.time.get_ticks()
            tiempo_transcurrido = tiempo_actual - self.ultimo_tiempo_recarga
            porcentaje = min(tiempo_transcurrido / self.tiempo_recarga_ataques, 1.0)
            
            # Dibuja la barra de recarga
            ancho_barra = 100
            alto_barra = 10
            x = self.x  # Cambiado de self.rect.x
            y = self.y - 30  # Cambiado de self.rect.y
            
            pygame.draw.rect(pantalla, (50, 50, 50), (x, y, ancho_barra, alto_barra))
            pygame.draw.rect(pantalla, (200, 200, 0), (x, y, ancho_barra * porcentaje, alto_barra))

    def puede_atacar_especial(self):
        """Verifica si puede realizar un ataque especial"""
        tiempo_actual = pygame.time.get_ticks()
        if tiempo_actual - self.ultimo_ataque_especial >= self.delay_entre_especiales:
            self.ultimo_ataque_especial = tiempo_actual
            return True
        return False

# ============= BUCLE PRINCIPAL DEL JUEGO =============
def dibujar_boton(pantalla, texto, x, y, ancho, alto, mouse_pos):
    """Dibuja un botón con estilo medieval"""
    rect = pygame.Rect(x, y, ancho, alto)
    hover = rect.collidepoint(mouse_pos)
    
    # Colores del botón
    color_borde = DORADO_CLARO if hover else DORADO
    color_fondo = MARRON_CLARO if hover else MARRON_OSCURO
    
    # Dibujar fondo del botón con bordes redondeados
    pygame.draw.rect(pantalla, color_fondo, rect, border_radius=10)
    pygame.draw.rect(pantalla, color_borde, rect, 3, border_radius=10)
    
    # Agregar detalles decorativos
    if hover:
        # Brillos en las esquinas cuando el mouse está encima
        pygame.draw.circle(pantalla, DORADO_CLARO, (x + 10, y + 10), 3)
        pygame.draw.circle(pantalla, DORADO_CLARO, (x + ancho - 10, y + 10), 3)
        pygame.draw.circle(pantalla, DORADO_CLARO, (x + 10, y + alto - 10), 3)
        pygame.draw.circle(pantalla, DORADO_CLARO, (x + ancho - 10, y + alto - 10), 3)
    
    # Texto del botón con sombra
    texto_surface = FUENTE_BOTONES.render(texto, True, MARRON_OSCURO if hover else DORADO_CLARO)
    texto_rect = texto_surface.get_rect(center=rect.center)
    
    # Dibujar sombra del texto
    sombra_surface = FUENTE_BOTONES.render(texto, True, MARRON_OSCURO)
    sombra_rect = sombra_surface.get_rect(center=(texto_rect.centerx + 2, texto_rect.centery + 2))
    pantalla.blit(sombra_surface, sombra_rect)
    
    # Dibujar texto principal
    pantalla.blit(texto_surface, texto_rect)
    
    return rect

def menu_instrucciones(pantalla):
    """Muestra el menú de instrucciones con estilo medieval y scroll"""
    instrucciones = [
        "",
          "Presiona ESC para volver",
        "Usa la rueda del ratón para desplazarte",
        "",
        "CONTROLES:",
        "Movimiento: WASD o Flechas",
        "Sprint: Barra espaciadora",
        "Ataque normal: Click izquierdo",
        "Ataque especial: Click derecho",
        "Dirigir el ataque con el ratón",
        "",
        "OBJETIVO:",
        "Derrota al puma usando tus ataques.",
        "¡Cuidado! El puma evoluciona al ser derrotado",
        "y se vuelve más fuerte.",
        "",
        "ITEMS:",
        "Rojo: Recupera vida",
        "Amarillo: Recupera energía",
        "",
      
    ]
    
    try:
        fondo_menu = pygame.image.load("images/fondo_menu.png")
        fondo_menu = pygame.transform.scale(fondo_menu, (ANCHO, ALTO))
    except:
        fondo_menu = None
    
    corriendo = True
    tiempo_inicial = pygame.time.get_ticks()
    scroll_y = 0  # Posición inicial del scroll en 0 para que comience arriba
    velocidad_scroll = 30  # Velocidad del scroll
    
    # Calcular altura total del contenido
    altura_total = 0
    for linea in instrucciones:
        if linea.endswith(":"):  # Títulos
            altura_total += 50
        elif linea:  # Texto normal
            altura_total += 35
        else:  # Línea en blanco
            altura_total += 20
    
    # Área visible del contenido
    margen = 50
    area_visible = ALTO - 2 * margen
    max_scroll = max(0, altura_total - area_visible)
    
    while corriendo:
        tiempo_actual = pygame.time.get_ticks()
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                return False
            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_ESCAPE:
                    scroll_y = 0  # Resetear el scroll al salir
                    return True
            if evento.type == pygame.MOUSEWHEEL:
                # Actualizar scroll con la rueda del ratón
                scroll_y = max(min(scroll_y - evento.y * velocidad_scroll, max_scroll), 0)
        
        # Dibujar fondo
        if fondo_menu:
            pantalla.blit(fondo_menu, (0, 0))
        else:
            pantalla.fill(MARRON_OSCURO)
        
        # Dibujar marco decorativo
        pygame.draw.rect(pantalla, MARRON_CLARO, 
                        (margen, margen, ANCHO - 2*margen, ALTO - 2*margen), 
                        border_radius=15)
        pygame.draw.rect(pantalla, DORADO, 
                        (margen, margen, ANCHO - 2*margen, ALTO - 2*margen), 
                        4, border_radius=15)
        
        # Crear superficie para clipear el contenido
        superficie_contenido = pygame.Surface((ANCHO - 2*margen, ALTO - 2*margen), pygame.SRCALPHA)
        
        # Dibujar texto con efectos en la superficie de contenido
        y = -scroll_y  # Comenzar desde la posición de scroll
        for linea in instrucciones:
            if linea.endswith(":"):  # Títulos
                # Efecto de brillo para títulos
                brillo = abs(math.sin((tiempo_actual - tiempo_inicial) * 0.002)) * 50
                color_titulo = (
                    min(255, DORADO_CLARO[0] + brillo),
                    min(255, DORADO_CLARO[1] + brillo),
                    min(255, DORADO_CLARO[2] + brillo)
                )
                texto = FUENTE_BOTONES.render(linea, True, color_titulo)
                sombra = FUENTE_BOTONES.render(linea, True, MARRON_OSCURO)
                rect = texto.get_rect(centerx=(ANCHO - 2*margen)//2, y=y)
                # Dibujar sombra y texto
                superficie_contenido.blit(sombra, (rect.x + 2, rect.y + 2))
                superficie_contenido.blit(texto, rect)
                y += 50
            elif linea:  # Texto normal
                texto = FUENTE_NORMAL.render(linea, True, CREMA)
                rect = texto.get_rect(centerx=(ANCHO - 2*margen)//2, y=y)
                superficie_contenido.blit(texto, rect)
                y += 35
            else:  # Línea en blanco
                y += 20
        
        # Dibujar la superficie de contenido en la pantalla
        pantalla.blit(superficie_contenido, (margen, margen))
        
        pygame.display.flip()
    
    return True

def menu_principal(pantalla):
    """Muestra el menú principal con estilo medieval"""
    try:
        fondo_menu = pygame.image.load("images/fondo_menu.png")
        fondo_menu = pygame.transform.scale(fondo_menu, (ANCHO, ALTO))
    except:
        print("⚠️ No se pudo cargar fondo_menu.png")
        fondo_menu = None
    
    ancho_boton = 250
    alto_boton = 60
    espacio_entre_botones = 30
    y_inicial = 300
    
    # Definir los botones fuera del bucle
    boton_jugar = pygame.Rect(
        ANCHO//2 - ancho_boton//2,
        y_inicial,
        ancho_boton,
        alto_boton
    )
    
    boton_instrucciones = pygame.Rect(
        ANCHO//2 - ancho_boton//2,
        y_inicial + alto_boton + espacio_entre_botones,
        ancho_boton,
        alto_boton
    )
    
    boton_salir = pygame.Rect(
        ANCHO//2 - ancho_boton//2,
        y_inicial + (alto_boton + espacio_entre_botones) * 2,
        ancho_boton,
        alto_boton
    )
    
    texto_titulo = FUENTE_TITULO.render("El Páramo", True, DORADO_CLARO)
    sombra_titulo = FUENTE_TITULO.render("El Páramo", True, MARRON_OSCURO)
    rect_titulo = texto_titulo.get_rect(center=(ANCHO//2, 120))
    
    corriendo = True
    while corriendo:
        mouse_pos = pygame.mouse.get_pos()
        tiempo = pygame.time.get_ticks()
        
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                return "salir"
            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_q:  # Añadida la tecla Q
                    return "salir"
            if evento.type == pygame.MOUSEBUTTONDOWN:
                if boton_jugar.collidepoint(mouse_pos):
                    return "jugar"
                elif boton_instrucciones.collidepoint(mouse_pos):
                    if menu_instrucciones(pantalla):
                        continue
                    return "salir"
                elif boton_salir.collidepoint(mouse_pos):
                    return "salir"
        
        # Dibujar el fondo
        if fondo_menu:
            pantalla.blit(fondo_menu, (0, 0))
        else:
            pantalla.fill(MARRON_OSCURO)
        
        # Efecto de brillo para el título
        brillo = abs(math.sin(tiempo * 0.002)) * 50
        color_titulo = (
            min(255, DORADO_CLARO[0] + brillo),
            min(255, DORADO_CLARO[1] + brillo),
            min(255, DORADO_CLARO[2] + brillo)
        )
        texto_titulo_brillante = FUENTE_TITULO.render("El Páramo", True, color_titulo)
        
        # Dibujar título
        pantalla.blit(sombra_titulo, (rect_titulo.x + 4, rect_titulo.y + 4))
        pantalla.blit(texto_titulo_brillante, rect_titulo)
        
        # Dibujar botones
        dibujar_boton(pantalla, "Jugar", boton_jugar.x, boton_jugar.y, ancho_boton, alto_boton, mouse_pos)
        dibujar_boton(pantalla, "Instrucciones", boton_instrucciones.x, boton_instrucciones.y, ancho_boton, alto_boton, mouse_pos)
        dibujar_boton(pantalla, "Salir", boton_salir.x, boton_salir.y, ancho_boton, alto_boton, mouse_pos)
        
        pygame.display.flip()
    
    return "salir"

def reproducir_cinematica(pantalla):
    """Reproduce una cinemática corta del puma entrando en escena"""
    # Crear los personajes
    oso = Personaje("oso", 200, 300)
    puma = Personaje("puma", ANCHO + 100, 300)
    
    # Configurar el puma
    puma.mirando_derecha = False
    puma.estado_animacion = 'walk'
    puma.frame_actual = 0
    puma.dx_actual = -1  # Indicar que está moviéndose hacia la izquierda
    puma.dy_actual = 0
    puma.moviendo_x = True
    puma.moviendo_y = False
    
    # Duración total de la cinemática: 3 segundos
    tiempo_inicio = pygame.time.get_ticks()
    duracion = 3000
    
    # Posición final del puma
    posicion_final_x = 500
    
    while True:
        tiempo_actual = pygame.time.get_ticks()
        tiempo_transcurrido = tiempo_actual - tiempo_inicio
        
        if tiempo_transcurrido >= duracion:
            break
            
        # Mover el puma suavemente hacia su posición final
        distancia_total = (ANCHO + 100) - posicion_final_x
        progreso = min(1.0, tiempo_transcurrido / duracion)
        puma.x = (ANCHO + 100) - (distancia_total * progreso)
        
        # Actualizar animación usando el método de la clase
        puma.actualizar_animacion()
        oso.actualizar_animacion()
        
        # Renderizar la escena
        if fondo:
            pantalla.blit(fondo, (0, 0))
        else:
            pantalla.fill(BLANCO)
            
        # Dibujar sombras
        dibujar_sombra(pantalla, oso.x, oso.y, oso.ancho, oso.alto)
        dibujar_sombra(pantalla, puma.x, puma.y, puma.ancho, puma.alto)
        
        # Dibujar personajes
        oso.dibujar(pantalla)
        puma.dibujar(pantalla)
        
        pygame.display.flip()
        reloj.tick(60)

def obtener_direccion(dx, dy):
    """Determina la dirección del ataque basado en el vector (dx, dy)"""
    angulo = math.atan2(dy, dx)
    grados = math.degrees(angulo)
    
    if -22.5 <= grados <= 22.5:
        return "derecha"
    elif 22.5 < grados <= 67.5:
        return "abajo-derecha"
    elif 67.5 < grados <= 112.5:
        return "abajo"
    elif 112.5 < grados <= 157.5:
        return "abajo-izquierda"
    elif grados > 157.5 or grados <= -157.5:
        return "izquierda"
    elif -157.5 < grados <= -112.5:
        return "arriba-izquierda"
    elif -112.5 < grados <= -67.5:
        return "arriba"
    else:  # -67.5 < grados <= -22.5
        return "arriba-derecha"

async def main():
    pygame.init()
    pantalla = pygame.display.set_mode((ANCHO, ALTO))
    pygame.display.set_caption(TITULO)
    
    while True:
        opcion = menu_principal(pantalla)
        if opcion == "jugar":
            reproducir_cinematica(pantalla)
            
            # Inicializar el juego
            jugador = Personaje("oso", 200, 300)
            enemigo = Personaje("puma", 500, 300)
            rocas = [
                Roca(100, 100),
                Roca(600, 400),
                Roca(300, 450)
            ]
            items_vida = []
            items_energia = []
            ultimo_item_vida = pygame.time.get_ticks()
            ultimo_item_energia = pygame.time.get_ticks()
            ultimo_ataque_enemigo = pygame.time.get_ticks()
            mensaje = None

            # Bucle principal del juego
            jugando = True
            while jugando:
                tiempo_actual = pygame.time.get_ticks()
                
                # Procesar eventos
                for evento in pygame.event.get():
                    if evento.type == pygame.QUIT:
                        return "salir"
                    if evento.type == pygame.KEYDOWN:
                        if evento.key == pygame.K_ESCAPE:
                            jugando = False
                        elif evento.key == pygame.K_q:  # Añadida la tecla Q
                            return "salir"  # Salir completamente del juego
                
                # Actualizar estado del juego
                teclas = pygame.key.get_pressed()
                mouse_pos = pygame.mouse.get_pos()
                botones_mouse = pygame.mouse.get_pressed()
                
                # Movimiento del jugador
                dx = dy = 0
                if teclas[pygame.K_LEFT] or teclas[pygame.K_a]:
                    dx = -1
                    jugador.mirando_derecha = False
                if teclas[pygame.K_RIGHT] or teclas[pygame.K_d]:
                    dx = 1
                    jugador.mirando_derecha = True
                if teclas[pygame.K_UP] or teclas[pygame.K_w]:
                    dy = -1
                if teclas[pygame.K_DOWN] or teclas[pygame.K_s]:
                    dy = 1

                # Sprint
                sprint_activado = teclas[pygame.K_SPACE]
                jugador.actualizar_sprint(sprint_activado)

                # Normalizar movimiento diagonal
                if dx != 0 and dy != 0:
                    dx *= 0.7071
                    dy *= 0.7071

                # Actualizar posición del jugador
                nueva_x = jugador.x + dx * jugador.velocidad_actual
                nueva_y = jugador.y + dy * jugador.velocidad_actual

                # Verificar colisiones con rocas y aplicar empuje suave
                centro_jugador_x = nueva_x + jugador.ancho/2
                centro_jugador_y = nueva_y + jugador.alto/2
                radio_jugador = min(jugador.ancho, jugador.alto) / 2.5

                for roca in rocas:
                    if roca.colisiona_con_circulo(centro_jugador_x, centro_jugador_y, radio_jugador):
                        # Calcular vector de empuje
                        dx_empuje = centro_jugador_x - roca.centro_x
                        dy_empuje = centro_jugador_y - roca.centro_y
                        distancia = max(1, math.sqrt(dx_empuje * dx_empuje + dy_empuje * dy_empuje))
                        
                        # Aplicar empuje suave
                        fuerza_empuje = 2.0
                        nueva_x += (dx_empuje / distancia) * fuerza_empuje
                        nueva_y += (dy_empuje / distancia) * fuerza_empuje

                # Aplicar límites de pantalla después del empuje
                jugador.x = max(0, min(ANCHO - jugador.ancho, nueva_x))
                jugador.y = max(0, min(ALTO - jugador.alto, nueva_y))

                # Actualizar estado de movimiento para animaciones
                jugador.moviendo_x = dx != 0
                jugador.moviendo_y = dy != 0
                
                if jugador.moviendo_x or jugador.moviendo_y:
                    jugador.estado_animacion = 'walk'
                else:
                    jugador.estado_animacion = 'idle'

                # Movimiento del enemigo
                enemigo.mover_ia(rocas, jugador)

                # Regeneración de energía
                if not sprint_activado:
                    jugador.energia = min(jugador.energia_maxima, jugador.energia + 0.2)

                # Ataques del jugador
                if botones_mouse[0]:  # Click izquierdo
                    if jugador.atacar_normal():
                        dx = mouse_pos[0] - (jugador.x + jugador.ancho/2)
                        dy = mouse_pos[1] - (jugador.y + jugador.alto/2)
                        direccion = obtener_direccion(dx, dy)
                        jugador.ataques.append(AtaqueRayo(
                            jugador.x + jugador.ancho/2,
                            jugador.y + jugador.alto/2,
                            direccion
                        ))
                        jugador.estado_animacion = 'attack'
                        jugador.frame_actual = 0
                        jugador.tiempo_ultimo_ataque = pygame.time.get_ticks()

                if botones_mouse[2]:  # Click derecho
                    if jugador.energia >= 20 and jugador.puede_atacar_especial():
                        sonido_ataque.play()  # Reproducir sonido de ataque
                        dx = mouse_pos[0] - (jugador.x + jugador.ancho/2)
                        dy = mouse_pos[1] - (jugador.y + jugador.alto/2)
                        direccion = obtener_direccion(dx, dy)
                        jugador.ataques.append(AtaqueRayo(
                            jugador.x + jugador.ancho/2,
                            jugador.y + jugador.alto/2,
                            direccion,
                            True
                        ))
                        jugador.energia -= 20
                        jugador.estado_animacion = 'attack'

                # Ataque automático del enemigo
                if tiempo_actual - ultimo_ataque_enemigo >= DELAY_ATAQUE_ENEMIGO:
                    if enemigo.evolucionado:
                        enemigo.estado_animacion = 'attack'
                        enemigo.frame_actual = 0
                    
                    dx = jugador.x - enemigo.x
                    dy = jugador.y - enemigo.y
                    direccion = obtener_direccion(dx, dy)
                    
                    enemigo.ataques.append(AtaqueFuego(
                        enemigo.x + enemigo.ancho/2,
                        enemigo.y + enemigo.alto/2,
                        direccion
                    ))
                    
                    if random.random() < (0.25 if enemigo.evolucionado else 0.15):
                        if enemigo.evolucionado:
                            enemigo.estado_animacion = 'attack'
                            enemigo.frame_actual = 0
                        enemigo.ataques.append(AtaqueEspecial(
                            enemigo.x + enemigo.ancho/2,
                            enemigo.y + enemigo.alto/2,
                            jugador
                        ))
                    
                    ultimo_ataque_enemigo = tiempo_actual

                # Mover y verificar colisiones de ataques
                for ataque in jugador.ataques[:]:
                    ataque.mover()
                    if isinstance(ataque, AtaqueRayo):
                        if ataque.x < 0 or ataque.x > ANCHO or ataque.y < 0 or ataque.y > ALTO:
                            jugador.ataques.remove(ataque)
                            continue
                        
                        for roca in rocas[:]:
                            if roca.colisiona_con_circulo(ataque.x, ataque.y, 15):
                                if roca.recibir_dano(10):
                                    rocas.remove(roca)
                                if ataque in jugador.ataques:
                                    jugador.ataques.remove(ataque)
                                break
                        
                        if ataque in jugador.ataques and detectar_colision_circular(
                            ataque.x, ataque.y, 15,
                            enemigo.x + enemigo.ancho/2,
                            enemigo.y + enemigo.alto/2,
                            min(enemigo.ancho, enemigo.alto) / 2.5
                        ):
                            enemigo.recibir_dano()
                            enemigo.vida -= 20 if isinstance(ataque, AtaqueRayo) and ataque.es_especial else 10
                            jugador.ataques.remove(ataque)
                            
                            if enemigo.vida <= 0 and not enemigo.evolucionado:
                                enemigo.evolucionar()

                # Mover y verificar colisiones de ataques enemigos
                for ataque in enemigo.ataques[:]:
                    ataque.mover()
                    if isinstance(ataque, AtaqueFuego):
                        if ataque.x < 0 or ataque.x > ANCHO or ataque.y < 0 or ataque.y > ALTO:
                            enemigo.ataques.remove(ataque)
                            continue
                    elif isinstance(ataque, AtaqueEspecial):
                        if ataque.ha_expirado():
                            enemigo.ataques.remove(ataque)
                            continue
                    
                    for roca in rocas[:]:
                        if roca.colisiona_con_circulo(
                            ataque.x + 15, ataque.y + 15, 15,
                            roca.centro_x, roca.centro_y, roca.radio
                        ):
                            if roca.recibir_dano(10):
                                rocas.remove(roca)
                            if ataque in enemigo.ataques:
                                enemigo.ataques.remove(ataque)
                            break
                    
                    if ataque in enemigo.ataques:
                        if (isinstance(ataque, AtaqueFuego) and detectar_colision_circular(
                            ataque.x + 10, ataque.y + 10, 10,
                            jugador.x + jugador.ancho/2,
                            jugador.y + jugador.alto/2,
                            min(jugador.ancho, jugador.alto) / 2.5
                        )) or (isinstance(ataque, AtaqueEspecial) and ataque.colisiona_con_jugador(jugador)):
                            if not jugador.invulnerable:
                                jugador.recibir_dano()
                                jugador.vida -= 15 if isinstance(ataque, AtaqueEspecial) else 10
                            enemigo.ataques.remove(ataque)

                # Generar items
                if tiempo_actual - ultimo_item_vida >= DELAY_ITEM_VIDA:
                    items_vida.append(ItemVida(
                        random.randint(50, ANCHO-50),
                        random.randint(50, ALTO-50)
                    ))
                    ultimo_item_vida = tiempo_actual

                if tiempo_actual - ultimo_item_energia >= DELAY_ITEM_ENERGIA:
                    items_energia.append(ItemEnergia(
                        random.randint(50, ANCHO-50),
                        random.randint(50, ALTO-50)
                    ))
                    ultimo_item_energia = tiempo_actual

                # Actualizar y verificar colisiones de items
                for item in items_vida[:]:
                    item.mover()
                    if item.ha_expirado():
                        items_vida.remove(item)
                    elif item.colisiona_con_jugador(jugador):
                        # Restaurar 30% de la vida máxima
                        cantidad_curacion = int(jugador.vida_maxima * 0.30)
                        jugador.vida = min(jugador.vida + cantidad_curacion, jugador.vida_maxima)
                        items_vida.remove(item)

                for item in items_energia[:]:
                    item.mover()
                    if item.ha_expirado():
                        items_energia.remove(item)
                    elif item.colisiona_con_jugador(jugador):
                        jugador.energia = min(jugador.energia + 30, jugador.energia_maxima)
                        items_energia.remove(item)

                # Verificar victoria/derrota
                if enemigo.vida <= 0:
                    try:
                        fondo_victoria = pygame.image.load("images/fondo_ganar.png")
                        fondo_victoria = pygame.transform.scale(fondo_victoria, (ANCHO, ALTO))
                    except:
                        print("⚠️ No se pudo cargar fondo_ganar.png")
                        fondo_victoria = None

                    # Bucle de la pantalla de victoria
                    while True:
                        for evento in pygame.event.get():
                            if evento.type == pygame.QUIT:
                                return "salir"
                            if evento.type == pygame.KEYDOWN:
                                if evento.key == pygame.K_ESCAPE:
                                    jugando = False
                                    break

                        # Dibujar fondo de victoria
                        if fondo_victoria:
                            pantalla.blit(fondo_victoria, (0, 0))
                        else:
                            # Crear un gradiente dorado si no hay imagen
                            for y in range(ALTO):
                                color = (
                                    min(255, 100 + y//2),
                                    min(255, 80 + y//3),
                                    min(100, 20 + y//6)
                                )
                                pygame.draw.line(pantalla, color, (0, y), (ANCHO, y))

                        # Renderizar texto "¡GANASTE!"
                        texto_victoria = FUENTE_TITULO.render("¡GANASTE!", True, DORADO_CLARO)
                        sombra_victoria = FUENTE_TITULO.render("¡GANASTE!", True, MARRON_OSCURO)
                        
                        # Posicionar el texto en la parte superior
                        rect_texto = texto_victoria.get_rect(center=(ANCHO//2, 120))
                        
                        # Dibujar sombra y texto
                        pantalla.blit(sombra_victoria, (rect_texto.x + 4, rect_texto.y + 4))
                        pantalla.blit(texto_victoria, rect_texto)

                        # Mensaje para volver al menú
                        texto_volver = FUENTE_NORMAL.render("Presiona ESC para volver al menú principal", True, BLANCO)
                        rect_volver = texto_volver.get_rect(center=(ANCHO//2, ALTO - 50))
                        pantalla.blit(texto_volver, rect_volver)

                        pygame.display.flip()
                        reloj.tick(60)

                    jugando = False
                elif jugador.vida <= 0:
                    mensaje = "Has sido derrotado"
                    jugando = False

                # Actualizar ataques normales
                jugador.actualizar_ataques_normales()

                # Actualizar rocas (añadir esto antes del bloque de dibujo)
                for roca in rocas[:]:
                    if roca.actualizar():
                        rocas.remove(roca)
                        # Generar nueva roca en posición aleatoria
                        x, y = generar_posicion_roca_aleatoria()
                        rocas.append(Roca(x, y))

                # Dibujar todo
                if fondo:
                    pantalla.blit(fondo, (0, 0))
                else:
                    pantalla.fill(BLANCO)

                for roca in rocas:
                    roca.dibujar(pantalla)

                for item in items_vida:
                    item.dibujar(pantalla)

                for item in items_energia:
                    item.dibujar(pantalla)

                for ataque in jugador.ataques:
                    ataque.dibujar(pantalla)

                for ataque in enemigo.ataques:
                    ataque.dibujar(pantalla)

                jugador.dibujar(pantalla)
                enemigo.dibujar(pantalla)

                jugador.dibujar_barra_vida(pantalla)
                enemigo.dibujar_barra_vida(pantalla)
                
                if jugador.ataques_normales_disponibles < jugador.ataques_normales_maximos:
                    jugador.dibujar_barra_ataques(pantalla)

                pygame.display.flip()
                reloj.tick(60)
                
        elif opcion == "salir":
            break
    
    pygame.quit()

# Añadir esta función después de mantener_en_pantalla
def generar_posicion_roca_aleatoria():
    """Genera una posición aleatoria para una nueva roca"""
    margen = 100  # Margen para evitar que aparezcan muy cerca de los bordes
    x = random.randint(margen, ANCHO - margen - 80)  # 80 es el ancho de la roca
    y = random.randint(margen, ALTO - margen - 80)   # 80 es el alto de la roca
    return x, y

if __name__ == "__main__":
    asyncio.run(main())
