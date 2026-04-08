<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import maplibregl from 'maplibre-gl'

type GeometryType = 'point' | 'polygon'

type GeoPoint = {
  type: 'Point'
  coordinates: [number, number]
}

type GeoPolygon = {
  type: 'Polygon'
  coordinates: number[][][]
}

type GeoGeometry = GeoPoint | GeoPolygon

const props = withDefaults(
  defineProps<{
    modelValue: unknown
    geometryType: GeometryType
    readonly?: boolean
    height?: number
  }>(),
  {
    readonly: false,
    height: 280
  }
)

const emit = defineEmits<{
  (event: 'update:modelValue', value: GeoGeometry | null): void
}>()

const mapContainer = ref<HTMLElement | null>(null)
const rawJson = ref('')
const parseError = ref('')

let map: maplibregl.Map | null = null
let mapReady = false
let polygonDraft: [number, number][] = []
const sourceId = `geo-source-${Math.random().toString(36).slice(2)}`
const pointPlaceholder = '{ "type": "Point", "coordinates": [37.62, 55.75] }'
const polygonPlaceholder = '{ "type": "Polygon", "coordinates": [[[37.6,55.7],[37.7,55.7],[37.7,55.8],[37.6,55.7]]] }'

const hasGeometry = computed(() => Boolean(parseGeometry(props.modelValue, props.geometryType)))

function toNumber(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string' && value.trim()) {
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : null
  }
  return null
}

function parsePointLike(value: unknown): GeoPoint | null {
  if (!value || typeof value !== 'object') return null
  const source = value as Record<string, unknown>

  if (source.type === 'Point' && Array.isArray(source.coordinates) && source.coordinates.length >= 2) {
    const lng = toNumber(source.coordinates[0])
    const lat = toNumber(source.coordinates[1])
    if (lng !== null && lat !== null) {
      return { type: 'Point', coordinates: [lng, lat] }
    }
  }

  const lat = toNumber(source.lat ?? source.latitude)
  const lng = toNumber(source.lng ?? source.lon ?? source.longitude)
  if (lat !== null && lng !== null) {
    return { type: 'Point', coordinates: [lng, lat] }
  }

  return null
}

function normalizePolygonRing(ring: unknown): [number, number][] {
  if (!Array.isArray(ring)) return []

  const result: [number, number][] = []
  for (const item of ring) {
    if (!Array.isArray(item) || item.length < 2) continue
    const lng = toNumber(item[0])
    const lat = toNumber(item[1])
    if (lng === null || lat === null) continue
    result.push([lng, lat])
  }

  return result
}

function ensureClosedRing(ring: [number, number][]): [number, number][] {
  if (ring.length < 3) return ring
  const first = ring[0]
  const last = ring[ring.length - 1]
  if (first[0] === last[0] && first[1] === last[1]) return ring
  return [...ring, [first[0], first[1]]]
}

function toRingTuples(ring: number[][]): [number, number][] {
  return ring
    .filter((item): item is [number, number] => Array.isArray(item) && item.length >= 2)
    .map((item): [number, number] => [Number(item[0]), Number(item[1])])
    .filter((item) => Number.isFinite(item[0]) && Number.isFinite(item[1]))
}

function parsePolygonLike(value: unknown): GeoPolygon | null {
  if (!value || typeof value !== 'object') return null
  const source = value as Record<string, unknown>

  if (source.type === 'Polygon' && Array.isArray(source.coordinates) && source.coordinates.length > 0) {
    const firstRing = normalizePolygonRing(source.coordinates[0])
    const closed = ensureClosedRing(firstRing)
    if (closed.length >= 4) {
      return { type: 'Polygon', coordinates: [closed] }
    }
  }

  if (Array.isArray(source.coordinates)) {
    const point = parsePointLike(source)
    if (point) {
      return {
        type: 'Polygon',
        coordinates: [[point.coordinates, point.coordinates, point.coordinates, point.coordinates]]
      }
    }
  }

  return null
}

function parseGeometry(value: unknown, geometryType: GeometryType): GeoGeometry | null {
  if (value === null || value === undefined || value === '') return null

  const prepared = typeof value === 'string' ? value.trim() : value
  if (prepared === '') return null

  let source: unknown = prepared
  if (typeof prepared === 'string') {
    try {
      source = JSON.parse(prepared)
    } catch {
      return null
    }
  }

  if (geometryType === 'point') {
    return parsePointLike(source)
  }

  return parsePolygonLike(source)
}

function geometryToJson(geometry: GeoGeometry | null): string {
  if (!geometry) return ''
  return JSON.stringify(geometry, null, 2)
}

function updateFromModelValue() {
  const geometry = parseGeometry(props.modelValue, props.geometryType)
  rawJson.value = geometryToJson(geometry)
  parseError.value = ''

  if (props.geometryType === 'polygon') {
    polygonDraft = geometry?.type === 'Polygon' ? toRingTuples(geometry.coordinates[0] ?? []) : []
    if (polygonDraft.length > 1) {
      const first = polygonDraft[0]
      const last = polygonDraft[polygonDraft.length - 1]
      if (first[0] === last[0] && first[1] === last[1]) {
        polygonDraft = polygonDraft.slice(0, -1)
      }
    }
  }

  renderMapGeometry(geometry)
}

function emitGeometry(geometry: GeoGeometry | null) {
  emit('update:modelValue', geometry)
}

function applyGeometry(geometry: GeoGeometry | null) {
  rawJson.value = geometryToJson(geometry)
  parseError.value = ''
  renderMapGeometry(geometry)
  emitGeometry(geometry)
}

function getFeatureCollection(geometry: GeoGeometry | null) {
  return {
    type: 'FeatureCollection',
    features: geometry
      ? [
          {
            type: 'Feature',
            properties: {},
            geometry
          }
        ]
      : []
  }
}

function fitToGeometry(geometry: GeoGeometry | null) {
  if (!map || !geometry) return

  if (geometry.type === 'Point') {
    map.flyTo({ center: geometry.coordinates, zoom: 13 })
    return
  }

  const bounds = new maplibregl.LngLatBounds()
  for (const coordinate of geometry.coordinates[0] ?? []) {
    bounds.extend(coordinate as [number, number])
  }
  if (!bounds.isEmpty()) {
    map.fitBounds(bounds, { padding: 30, duration: 350, maxZoom: 15 })
  }
}

function renderMapGeometry(geometry: GeoGeometry | null) {
  if (!map || !mapReady) return
  const source = map.getSource(sourceId) as maplibregl.GeoJSONSource | undefined
  if (!source) return
  source.setData(getFeatureCollection(geometry) as any)
}

function onMapClick(event: maplibregl.MapMouseEvent) {
  if (props.readonly) return

  const nextPoint: [number, number] = [event.lngLat.lng, event.lngLat.lat]

  if (props.geometryType === 'point') {
    applyGeometry({ type: 'Point', coordinates: nextPoint })
    return
  }

  polygonDraft = [...polygonDraft, nextPoint]
  if (polygonDraft.length >= 3) {
    const polygon: GeoPolygon = {
      type: 'Polygon',
      coordinates: [ensureClosedRing(polygonDraft)]
    }
    applyGeometry(polygon)
    return
  }

  renderMapGeometry({
    type: 'Polygon',
    coordinates: [polygonDraft]
  })
}

function closePolygon() {
  if (props.readonly || props.geometryType !== 'polygon') return
  if (polygonDraft.length < 3) return

  applyGeometry({
    type: 'Polygon',
    coordinates: [ensureClosedRing(polygonDraft)]
  })
}

function clearGeometry() {
  if (props.readonly) return
  polygonDraft = []
  applyGeometry(null)
}

function moveToUserLocation() {
  if (!map || !navigator.geolocation) return

  navigator.geolocation.getCurrentPosition(
    (position) => {
      const lngLat: [number, number] = [position.coords.longitude, position.coords.latitude]
      map?.flyTo({ center: lngLat, zoom: 14 })

      if (!props.readonly && props.geometryType === 'point') {
        applyGeometry({ type: 'Point', coordinates: lngLat })
      }
    },
    () => {
      parseError.value = 'Не удалось определить геолокацию.'
    },
    { enableHighAccuracy: true, timeout: 10000 }
  )
}

function onJsonInput(value: string) {
  rawJson.value = value

  if (!value.trim()) {
    parseError.value = ''
    polygonDraft = []
    renderMapGeometry(null)
    emitGeometry(null)
    return
  }

  const geometry = parseGeometry(value, props.geometryType)
  if (!geometry) {
    parseError.value = 'Некорректный GeoJSON для выбранного типа геометрии.'
    return
  }

  parseError.value = ''
  if (geometry.type === 'Polygon') {
    polygonDraft = toRingTuples(geometry.coordinates[0] ?? [])
    if (polygonDraft.length > 1) {
      const first = polygonDraft[0]
      const last = polygonDraft[polygonDraft.length - 1]
      if (first[0] === last[0] && first[1] === last[1]) {
        polygonDraft = polygonDraft.slice(0, -1)
      }
    }
  }

  renderMapGeometry(geometry)
  emitGeometry(geometry)
}

function initMap() {
  if (!mapContainer.value || map) return

  map = new maplibregl.Map({
    container: mapContainer.value,
    style: 'https://demotiles.maplibre.org/style.json',
    center: [37.6173, 55.7558],
    zoom: 3
  })

  map.addControl(new maplibregl.NavigationControl({ showCompass: true }), 'top-right')

  map.on('load', () => {
    if (!map) return
    mapReady = true

    map.addSource(sourceId, {
      type: 'geojson',
      data: getFeatureCollection(parseGeometry(props.modelValue, props.geometryType)) as any
    })

    map.addLayer({
      id: `${sourceId}-point`,
      type: 'circle',
      source: sourceId,
      filter: ['==', '$type', 'Point'],
      paint: {
        'circle-radius': 7,
        'circle-color': '#1b7f76',
        'circle-stroke-width': 2,
        'circle-stroke-color': '#ffffff'
      }
    })

    map.addLayer({
      id: `${sourceId}-polygon-fill`,
      type: 'fill',
      source: sourceId,
      filter: ['==', '$type', 'Polygon'],
      paint: {
        'fill-color': '#1b7f76',
        'fill-opacity': 0.24
      }
    })

    map.addLayer({
      id: `${sourceId}-polygon-line`,
      type: 'line',
      source: sourceId,
      filter: ['==', '$type', 'Polygon'],
      paint: {
        'line-color': '#1b7f76',
        'line-width': 2
      }
    })

    const geometry = parseGeometry(props.modelValue, props.geometryType)
    renderMapGeometry(geometry)
    fitToGeometry(geometry)
  })

  map.on('click', onMapClick)
}

onMounted(async () => {
  await nextTick()
  updateFromModelValue()
  initMap()
})

watch(
  () => props.modelValue,
  () => {
    updateFromModelValue()
  }
)

watch(
  () => props.geometryType,
  () => {
    polygonDraft = []
    updateFromModelValue()
  }
)

onBeforeUnmount(() => {
  if (map) {
    map.remove()
    map = null
    mapReady = false
  }
})
</script>

<template>
  <div class="geo-editor" :class="{ readonly: readonly }">
    <div class="geo-editor-toolbar">
      <span>{{ geometryType === 'point' ? 'Точка' : 'Полигон' }}</span>
      <div class="geo-editor-actions">
        <button type="button" class="small-btn" @click="moveToUserLocation">Моя геолокация</button>
        <button
          v-if="geometryType === 'polygon'"
          type="button"
          class="small-btn"
          :disabled="readonly || polygonDraft.length < 3"
          @click="closePolygon"
        >
          Замкнуть полигон
        </button>
        <button type="button" class="small-btn danger" :disabled="readonly || !hasGeometry" @click="clearGeometry">
          Очистить
        </button>
      </div>
    </div>

    <div class="geo-editor-layout">
      <div ref="mapContainer" class="geo-map" :style="{ height: `${height}px` }" />
      <textarea
        class="geo-json"
        :value="rawJson"
        :readonly="readonly"
        :placeholder="geometryType === 'point' ? pointPlaceholder : polygonPlaceholder"
        @input="onJsonInput(($event.target as HTMLTextAreaElement).value)"
      />
    </div>

    <p v-if="parseError" class="geo-error">{{ parseError }}</p>
  </div>
</template>

<style scoped>
.geo-editor {
  display: grid;
  gap: 8px;
}

.geo-editor-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.geo-editor-actions {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.small-btn {
  border: 1px solid var(--line);
  background: var(--bg-soft);
  color: var(--text-main);
  border-radius: 10px;
  padding: 6px 10px;
  font-size: 0.78rem;
  cursor: pointer;
}

.small-btn.danger {
  border-color: color-mix(in srgb, var(--danger) 45%, var(--line));
  color: var(--danger);
}

.small-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.geo-editor-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.geo-map {
  border: 1px solid var(--line);
  border-radius: 12px;
  overflow: hidden;
  min-height: 220px;
}

.geo-json {
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--bg-soft);
  color: var(--text-main);
  font: 12px/1.45 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  padding: 10px;
  resize: vertical;
  min-height: 220px;
}

.geo-error {
  margin: 0;
  color: var(--danger);
  font-size: 0.82rem;
}

@media (max-width: 980px) {
  .geo-editor-layout {
    grid-template-columns: 1fr;
  }

  .geo-map,
  .geo-json {
    min-height: 180px;
  }
}
</style>
