declare module "plotly.js-dist-min" {
  const Plotly: unknown;
  export default Plotly;
}

declare module "plotly.js/lib/core" {
  const Plotly: {
    register: (modules: unknown[]) => void;
  };
  export default Plotly;
}

declare module "plotly.js/lib/scatter" {
  const scatter: unknown;
  export default scatter;
}

declare module "plotly.js/lib/scattergl" {
  const scattergl: unknown;
  export default scattergl;
}

declare module "react-plotly.js/factory" {
  import type { ComponentType } from "react";

  export type PlotlyComponentProps = {
    data?: unknown;
    layout?: unknown;
    config?: unknown;
    revision?: number;
    useResizeHandler?: boolean;
    className?: string;
  };

  export default function createPlotlyComponent(plotly: unknown): ComponentType<PlotlyComponentProps>;
}
