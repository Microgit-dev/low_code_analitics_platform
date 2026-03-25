<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerIcon   from 'leaflet/dist/images/marker-icon.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'

// Fix Leaflet default icon in Vite
delete (L.Icon.Default.prototype as any)._getIconUrl
L.Icon.Default.mergeOptions({ iconUrl: markerIcon, iconRetinaUrl: markerIcon2x, shadowUrl: markerShadow })

const props = defineProps<{
  modelValue: [number, number] | null
  label?: string
}>()
const emit = defineEmits<{ 'update:modelValue': [[number, number]] }>()

const mapRef = ref<HTMLElement | null>(null)
let map: L.Map | null = null
let marker: L.Marker | null = null

onMounted(() => {
  if (!mapRef.value) return

  const center: L.LatLngExpression = props.modelValue ?? [54.92, 37.41]
  map = L.map(mapRef.value).setView(center, 12)

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© <a href="https://openstreetmap.org">OpenStreetMap</a>',
    maxZoom: 19,
  }).addTo(map)

  if (props.modelValue) {
    marker = L.marker(props.modelValue).addTo(map)
  }

  map.on('click', (e: L.LeafletMouseEvent) => {
    const { lat, lng } = e.latlng
    if (marker) marker.setLatLng([lat, lng])
    else marker = L.marker([lat, lng]).addTo(map!)
    emit('update:modelValue', [lat, lng])
  })
})

watch(() => props.modelValue, (val) => {
  if (!val || !map) return
  if (marker) marker.setLatLng(val)
  else marker = L.marker(val).addTo(map)
  map.setView(val)
})

onUnmounted(() => { map?.remove() })
</script>

<template>
  <div class="map-wrap">
    <div ref="mapRef" class="map-el" />
    <p v-if="modelValue" class="map-coords">
      {{ modelValue[0].toFixed(5) }}, {{ modelValue[1].toFixed(5) }}
    </p>
    <p v-else class="map-hint">Нажмите на карту, чтобы выбрать место</p>
  </div>
</template>

<style scoped>
.map-wrap {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.map-el {
  height: 260px;
  border-radius: 12px;
  overflow: hidden;
  border: 1.5px solid #d3dee2;
}
.map-coords {
  font-size: 12px;
  color: #2f8486;
  font-family: monospace;
  margin: 0;
}
.map-hint {
  font-size: 12px;
  color: #b0bac8;
  margin: 0;
}
</style>
