import {Slider as SliderPrimitive} from "@base-ui/react/slider";
import {cn} from "cn";

function Slider({
    className,
    "aria-label": ariaLabel,
    "aria-labelledby": ariaLabelledBy,
    "aria-describedby": ariaDescribedBy,
    ...props
}) {
    return (
        <SliderPrimitive.Root
            data-slot="slider"
            className={cn("w-full px-3 data-disabled:opacity-50", className)}
            {...props}
        >
            <SliderPrimitive.Control
                data-slot="slider-control"
                className="relative flex h-8 w-full cursor-pointer touch-none items-center select-none data-disabled:cursor-not-allowed"
            >
                <SliderPrimitive.Track
                    data-slot="slider-track"
                    className="h-1.5 w-full overflow-hidden rounded-full bg-muted"
                >
                    <SliderPrimitive.Indicator
                        data-slot="slider-indicator"
                        className="h-full rounded-full bg-primary"
                    />
                </SliderPrimitive.Track>
                <SliderPrimitive.Thumb
                    data-slot="slider-thumb"
                    className="group/slider-thumb grid size-6 cursor-grab place-items-center data-disabled:cursor-not-allowed data-dragging:cursor-grabbing"
                    aria-label={ariaLabel}
                    aria-labelledby={ariaLabelledBy}
                    aria-describedby={ariaDescribedBy}
                >
                    <span
                        aria-hidden="true"
                        className="pointer-events-none size-3.5 rounded-full border border-primary bg-background shadow-xs transition-shadow group-has-[:focus-visible]/slider-thumb:ring-3 group-has-[:focus-visible]/slider-thumb:ring-ring/50"
                    />
                </SliderPrimitive.Thumb>
            </SliderPrimitive.Control>
        </SliderPrimitive.Root>
    );
}

export {Slider};
