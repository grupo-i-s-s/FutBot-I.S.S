import {useEffect, useState} from 'react';
import {
    Combobox,
    ComboboxContent,
    ComboboxEmpty,
    ComboboxInput,
    ComboboxItem,
    ComboboxList,
} from '@/components/ui/combobox';
import {listPlayers} from '../api';

const playerLabel = (player) => player.name;
const samePlayer = (item, value) => item.id === value.id;

export default function TeamPlayerCombobox({id, player, excludedPlayerIds, disabled, onSelect}) {
    const [open, setOpen] = useState(false);
    const [query, setQuery] = useState(null);
    const [result, setResult] = useState(null);
    const search = query?.trim() ?? '';
    const currentResult = result?.search === search ? result : null;
    const options = (currentResult?.items ?? []).filter(
        (item) => !excludedPlayerIds.includes(String(item.id)),
    );

    useEffect(() => {
        if (!open || disabled) return;

        const controller = new AbortController();
        const timer = setTimeout(async () => {
            try {
                const {items} = await listPlayers({search, page: 1, limit: 10, signal: controller.signal});
                if (!controller.signal.aborted) setResult({search, items});
            } catch (error) {
                if (!controller.signal.aborted) {
                    setResult({search, error: error.message || 'No se pudieron buscar jugadores.'});
                }
            }
        }, search ? 250 : 0);

        return () => {
            clearTimeout(timer);
            controller.abort();
        };
    }, [disabled, open, search]);

    function handleOpenChange(nextOpen) {
        setOpen(nextOpen);
        if (!nextOpen) {
            setQuery(null);
            setResult(null);
        }
    }

    return (
        <Combobox
            disabled={disabled}
            open={open}
            onOpenChange={handleOpenChange}
            value={player}
            inputValue={query ?? player?.name ?? ''}
            items={options}
            filter={null}
            itemToStringLabel={playerLabel}
            isItemEqualToValue={samePlayer}
            autoHighlight="always"
            onInputValueChange={(value, {reason}) => {
                if (reason === 'input-change') {
                    setQuery(value);
                    setOpen(true);
                }
            }}
            onValueChange={(item, details) => {
                if (!item || excludedPlayerIds.includes(String(item.id))) {
                    details.cancel();
                    return;
                }
                if (!player || !samePlayer(item, player)) onSelect(item);
            }}
        >
            <ComboboxInput
                id={id}
                className="w-full"
                placeholder="Buscar jugador"
                onKeyDown={(event) => {
                    if (event.key === 'Enter' && !event.nativeEvent.isComposing) event.preventDefault();
                }}
            />
            <ComboboxContent>
                <ComboboxEmpty>
                    {!currentResult
                        ? 'Buscando jugadores…'
                        : currentResult.error || 'No se encontraron jugadores disponibles.'}
                </ComboboxEmpty>
                <ComboboxList>
                    {(item) => <ComboboxItem key={item.id} value={item}>{item.name}</ComboboxItem>}
                </ComboboxList>
            </ComboboxContent>
        </Combobox>
    );
}
