declare module "lucide-react";

declare module "@base-ui/react/button" {
  import * as React from "react";

  export namespace Button {
    export type Props = React.ButtonHTMLAttributes<HTMLButtonElement> & {
      render?: React.ReactElement | ((props: Record<string, unknown>) => React.ReactNode);
      nativeButton?: boolean;
    };
  }

  export const Button: React.ForwardRefExoticComponent<
    Button.Props & React.RefAttributes<HTMLButtonElement>
  >;
}

