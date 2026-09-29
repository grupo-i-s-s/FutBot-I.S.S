import {useState} from 'react';
import {Button} from '@/components/ui/button';
import {
    Dialog,
    DialogClose,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import {
    Field,
    FieldContent,
    FieldDescription,
    FieldError,
    FieldGroup,
    FieldLabel,
    FieldLegend,
    FieldSet,
} from '@/components/ui/field';
import {Input} from '@/components/ui/input';
import {Switch} from '@/components/ui/switch';
import {ToggleGroup, ToggleGroupItem} from '@/components/ui/toggle-group';
import {AVATAR_OPTIONS} from '../avatars';
import ClubAvatar from './ClubAvatar';

const MAX_NAME_LENGTH = 50;

export default function ClubSettingsDialog({club, isOpen, onOpenChange, onSave}) {
    return (
        <Dialog open={isOpen} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-md">
                {/* Se monta al abrir: el formulario arranca con los datos actuales del club. */}
                {isOpen && <ClubSettingsForm club={club} onSave={onSave}/>}
            </DialogContent>
        </Dialog>
    );
}

function ClubSettingsForm({club, onSave}) {
    const [clubName, setClubName] = useState(club.name);
    const [avatar, setAvatar] = useState(club.avatar);
    const [isFriendlyAvailable, setIsFriendlyAvailable] = useState(club.friendlyAvailable);
    const [nameError, setNameError] = useState('');

    function handleSubmit(event) {
        event.preventDefault();
        const trimmedName = clubName.trim();
        if (!trimmedName) {
            setNameError('Ingresá el nombre del club.');
            return;
        }
        if (trimmedName.length > MAX_NAME_LENGTH) {
            setNameError(`El nombre no puede superar los ${MAX_NAME_LENGTH} caracteres.`);
            return;
        }
        onSave({name: trimmedName, avatar, friendlyAvailable: isFriendlyAvailable});
    }

    function handleAvatarChange(values) {
        // ToggleGroup devuelve un array; se ignora el intento de deseleccionar.
        if (values.length > 0) setAvatar(values[0]);
    }

    return (
        <form onSubmit={handleSubmit} noValidate className="grid gap-4">
            <DialogHeader>
                <DialogTitle className="text-lg font-bold">Configurar club</DialogTitle>
                <DialogDescription>Cambiá el nombre, el avatar y la disponibilidad para amistosos.</DialogDescription>
            </DialogHeader>

            <FieldGroup>
                <Field data-invalid={Boolean(nameError)}>
                    <FieldLabel htmlFor="club-name">Nombre del club</FieldLabel>
                    <Input
                        id="club-name"
                        value={clubName}
                        maxLength={MAX_NAME_LENGTH}
                        onChange={(event) => {
                            setClubName(event.target.value);
                            setNameError('');
                        }}
                        aria-invalid={Boolean(nameError)}
                    />
                    <FieldError>{nameError}</FieldError>
                </Field>

                <FieldSet>
                    <FieldLegend variant="label">Avatar</FieldLegend>
                    <ToggleGroup
                        value={[avatar]}
                        onValueChange={handleAvatarChange}
                        variant="outline"
                        spacing={2}
                        className="grid w-full grid-cols-3 sm:grid-cols-6"
                    >
                        {AVATAR_OPTIONS.map((option) => (
                            <ToggleGroupItem
                                key={option.key}
                                value={option.key}
                                aria-label={option.label}
                                title={option.label}
                                className="h-auto flex-col gap-1 py-2 text-xs data-pressed:border-primary data-pressed:ring-2 data-pressed:ring-primary"
                            >
                                <ClubAvatar avatar={option.key} clubName={clubName} size="md"/>
                                {option.label}
                            </ToggleGroupItem>
                        ))}
                    </ToggleGroup>
                </FieldSet>

                <Field orientation="horizontal">
                    <FieldContent>
                        <FieldLabel htmlFor="friendly-available">Disponible para amistosos</FieldLabel>
                        <FieldDescription>Otros clubes podrán invitarte a jugar.</FieldDescription>
                    </FieldContent>
                    <Switch
                        id="friendly-available"
                        checked={isFriendlyAvailable}
                        onCheckedChange={setIsFriendlyAvailable}
                    />
                </Field>
            </FieldGroup>

            <DialogFooter>
                <DialogClose render={<Button type="button" variant="outline"/>}>Cancelar</DialogClose>
                <Button type="submit">Guardar cambios</Button>
            </DialogFooter>
        </form>
    );
}