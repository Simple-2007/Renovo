// Своя сборка ECharts для Renovo: только то, чем пользуется страница
// мониторинга. Полный echarts.min.js весит около мегабайта; здесь линия,
// сетка, подсказка, зум (щипком/колесом и рамкой), панель инструментов и
// раскладка подписей — она разводит концевые подписи, когда линии сходятся.
// Легенда своя, на кнопках, поэтому LegendComponent не нужен.
//
// Рамка зума в панели работает через общий DataZoomComponent: отдельного
// «select» в модульной сборке нет, а одного DataZoomInsideComponent панели
// не хватает — кнопка рамки просто ничего не делает.
//
// Пересборка: npm i echarts esbuild && esbuild entry.js --bundle --minify
//   --format=iife --target=es2019 --legal-comments=none
//   --outfile=static/telemetry/echarts.custom.js
import * as echarts from 'echarts/core';
import { LineChart } from 'echarts/charts';
import {
  GridComponent,
  TooltipComponent,
  DataZoomComponent,
  DataZoomInsideComponent,
  ToolboxComponent,
} from 'echarts/components';
import { LabelLayout } from 'echarts/features';
import { CanvasRenderer } from 'echarts/renderers';

echarts.use([
  LineChart,
  GridComponent,
  TooltipComponent,
  DataZoomComponent,
  DataZoomInsideComponent,
  ToolboxComponent,
  LabelLayout,
  CanvasRenderer,
]);

window.echarts = echarts;
