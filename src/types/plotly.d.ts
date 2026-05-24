declare module "plotly.js-dist-min" {
  const Plotly: unknown;
  export default Plotly;
}

declare module "react-plotly.js/factory" {
  import type { ComponentType } from "react";

  export type PlotlyComponentProps = {
    data?: unknown;
    layout?: unknown;
    config?: unknown;
    useResizeHandler?: boolean;
    className?: string;
  };

  export default function createPlotlyComponent(plotly: unknown): ComponentType<PlotlyComponentProps>;
}
