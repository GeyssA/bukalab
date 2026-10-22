<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis version="3.34.0" styleCategories="Symbology">
  <renderer-v2 type="graduatedSymbol" attr="temp_moyenne_2025" graduatedMethod="GraduatedColor"
               forceraster="0" symbollevels="0" enableorderby="0">
    <ranges>
      <range symbol="0" lower="4.99" upper="11.2" label="T1 5.0–11.2 °C" render="true"/>
      <range symbol="1" lower="11.2" upper="12.0" label="T2 11.2–12.0 °C" render="true"/>
      <range symbol="2" lower="12.0" upper="13.1" label="T3 12.0–13.1 °C" render="true"/>
      <range symbol="3" lower="13.1" upper="20.01" label="T4 13.1–20.0 °C" render="true"/>
    </ranges>
    <symbols>
      <symbol type="marker" name="0" alpha="1" force_rhr="0" clip_to_extent="1">
        <layer class="SimpleMarker" pass="0" enabled="1" locked="0">
          <prop k="color" v="245,239,230,255"/>
          <prop k="name" v="circle"/>
          <prop k="outline_style" v="no"/>
          <prop k="size" v="1.6"/>
        </layer>
      </symbol>
      <symbol type="marker" name="1" alpha="1" force_rhr="0" clip_to_extent="1">
        <layer class="SimpleMarker" pass="0" enabled="1" locked="0">
          <prop k="color" v="232,196,160,255"/>
          <prop k="name" v="circle"/>
          <prop k="outline_style" v="no"/>
          <prop k="size" v="1.6"/>
        </layer>
      </symbol>
      <symbol type="marker" name="2" alpha="1" force_rhr="0" clip_to_extent="1">
        <layer class="SimpleMarker" pass="0" enabled="1" locked="0">
          <prop k="color" v="200,90,42,255"/>
          <prop k="name" v="circle"/>
          <prop k="outline_style" v="no"/>
          <prop k="size" v="1.6"/>
        </layer>
      </symbol>
      <symbol type="marker" name="3" alpha="1" force_rhr="0" clip_to_extent="1">
        <layer class="SimpleMarker" pass="0" enabled="1" locked="0">
          <prop k="color" v="122,46,18,255"/>
          <prop k="name" v="circle"/>
          <prop k="outline_style" v="no"/>
          <prop k="size" v="1.6"/>
        </layer>
      </symbol>
    </symbols>
  </renderer-v2>
</qgis>
