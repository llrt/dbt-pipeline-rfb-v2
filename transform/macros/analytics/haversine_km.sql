{#- Distância haversine em km entre dois pontos (graus decimais), raio médio da Terra 6371.0088 km
    (ANA-04). `least(1, ...)` protege o `asin` de arredondamento acima de 1 em pontos antípodas. -#}
{% macro haversine_km(lat1, lon1, lat2, lon2) -%}
2 * 6371.0088 * asin(least(1.0, sqrt(
  pow(sin(radians(({{ lat2 }}) - ({{ lat1 }})) / 2), 2)
  + cos(radians({{ lat1 }})) * cos(radians({{ lat2 }}))
  * pow(sin(radians(({{ lon2 }}) - ({{ lon1 }})) / 2), 2)
)))
{%- endmacro %}
