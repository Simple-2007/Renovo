// Своя сборка ECharts для Renovo: только то, чем пользуется страница
// мониторинга. Полный echarts.min.js весит около мегабайта; здесь линия,
// сетка, подсказка и зум внутри области графика. Легенда своя, на кнопках,
// поэтому LegendComponent не нужен.
//
// Пересборка: npm i echarts esbuild && esbuild entry.js --bundle --minify
//   --format=iife --target=es2019 --legal-comments=none
//   --outfile=static/telemetry/echarts.custom.js
import * as echarts from 'echarts/core';
import { LineChart } from 'echarts/charts';
import {
  GridComponent,
  TooltipComponent,
  DataZoomInsideComponent,
} from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';

echarts.use([
  LineChart,
  GridComponent,
  TooltipComponent,
  DataZoomInsideComponent,
  CanvasRenderer,
]);

window.echarts = echarts;
