// pantallas.js — en qué borde de cada pantalla va la franja de Muyu: el que no toca a otro monitor (si no, al pasar
// el ratón de una pantalla a la otra, la franja abriría la rueda). Primero el derecho; si ahí hay otra pantalla, el
// izquierdo; si hay a los dos lados, arriba. `pantalla` y `todas` son QScreen (`pantallasQt`, con su `geometry`).
.pragma library

function solapanEnVertical(a, b) {
    return a.y < b.y + b.height && b.y < a.y + a.height
}

function lado(pantalla, todas) {
    const g = pantalla.geometry
    const otras = Array.from(todas).filter(o => o.name !== pantalla.name).map(o => o.geometry)
    const aLaDerecha = otras.some(o => o.x === g.x + g.width && solapanEnVertical(o, g))
    const aLaIzquierda = otras.some(o => o.x + o.width === g.x && solapanEnVertical(o, g))
    if (!aLaDerecha)
        return "derecha"
    if (!aLaIzquierda)
        return "izquierda"
    return "arriba"
}
