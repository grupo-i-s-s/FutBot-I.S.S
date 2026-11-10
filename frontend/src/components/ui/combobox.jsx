import {Combobox as ComboboxPrimitive} from '@base-ui/react/combobox';
import {Check, ChevronDown} from 'lucide-react';
import {cn} from 'cn';
import {Button} from '@/components/ui/button';
import {Input} from '@/components/ui/input';

const Combobox = ComboboxPrimitive.Root;

function ComboboxInput({className, ...props}) {
    return (
        <div className={cn('relative', className)}>
            <ComboboxPrimitive.Input
                data-slot="combobox-input"
                render={<Input className="pr-8" />}
                {...props}
            />
            <ComboboxPrimitive.Trigger
                data-slot="combobox-trigger"
                render={<Button type="button" variant="ghost" size="icon-xs" />}
                className="absolute inset-y-0 right-1 my-auto text-muted-foreground"
                aria-label="Mostrar opciones"
            >
                <ChevronDown aria-hidden="true" />
            </ComboboxPrimitive.Trigger>
        </div>
    );
}

function ComboboxContent({className, ...props}) {
    return (
        <ComboboxPrimitive.Portal>
            <ComboboxPrimitive.Positioner side="bottom" align="start" sideOffset={6} className="isolate z-50">
                <ComboboxPrimitive.Popup
                    data-slot="combobox-content"
                    className={cn('group/combobox-content w-(--anchor-width) max-w-(--available-width) overflow-hidden rounded-lg bg-popover text-popover-foreground shadow-md ring-1 ring-foreground/10', className)}
                    {...props}
                />
            </ComboboxPrimitive.Positioner>
        </ComboboxPrimitive.Portal>
    );
}

function ComboboxList({className, ...props}) {
    return (
        <ComboboxPrimitive.List
            data-slot="combobox-list"
            className={cn('max-h-[min(16rem,var(--available-height))] overflow-y-auto overscroll-contain p-1 data-empty:p-0', className)}
            {...props}
        />
    );
}

function ComboboxItem({className, children, ...props}) {
    return (
        <ComboboxPrimitive.Item
            data-slot="combobox-item"
            className={cn('relative flex w-full cursor-default items-center rounded-md py-1.5 pr-8 pl-2 text-sm outline-none select-none data-highlighted:bg-accent data-highlighted:text-accent-foreground', className)}
            {...props}
        >
            {children}
            <ComboboxPrimitive.ItemIndicator className="pointer-events-none absolute right-2">
                <Check className="size-4" aria-hidden="true" />
            </ComboboxPrimitive.ItemIndicator>
        </ComboboxPrimitive.Item>
    );
}

function ComboboxEmpty({className, ...props}) {
    return (
        <ComboboxPrimitive.Empty
            data-slot="combobox-empty"
            className={cn('hidden px-2 py-2 text-sm text-muted-foreground group-data-empty/combobox-content:block', className)}
            {...props}
        />
    );
}

export {Combobox, ComboboxInput, ComboboxContent, ComboboxList, ComboboxItem, ComboboxEmpty};
