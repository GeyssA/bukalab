<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis version="3.34.0" styleCategories="Symbology">
  <renderer-v2 type="graduatedSymbol" attr="precip_totale_2025" graduatedMethod="GraduatedColor"
               forceraster="0" symbollevels="0" enableorderby="0">
    <ranges>
      <range symbol="0" lower="299.99" upper="780.0" label="P1 300–780 mm" render="true"/>
      <range symbol="1" lower="780.0" upper="900.0" label="P2 780–900 mm" render="true"/>
      <range symbol="2" lower="900.0" upper="1040.0" label="P3 900–1040 mm" render="true"/>
      <range symbol="3" lower="1040.0" upper="2500.01" label="P4 1040–2500 mm" render="true"/>
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
          <prop k="color" v="197,212,224,255"/>
          <prop k="name" v="circle"/>
          <prop k="outline_style" v="no"/>
          <prop k="size" v="1.6"/>
        </layer>
      </symbol>
      <symbol type="marker" name="2" alpha="1" force_rhr="0" clip_to_extent="1">
        <layer class="SimpleMarker" pass="0" enabled="1" locked="0">
          <prop k="color" v="58,122,138,255"/>
          <prop k="name" v="circle"/>
          <prop k="outline_style" v="no"/>
          <prop k="size" v="1.6"/>
        </layer>
      </symbol>
      <symbol type="marker" name="3" alpha="1" force_rhr="0" clip_to_extent="1">
        <layer class="SimpleMarker" pass="0" enabled="1" locked="0">
          <prop k="color" v="26,58,92,255"/>
          <prop k="name" v="circle"/>
          <prop k="outline_style" v="no"/>
          <prop k="size" v="1.6"/>
        </layer>
      </symbol>
    </symbols>
  </renderer-v2>
</qgis>
