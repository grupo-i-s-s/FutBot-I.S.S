import {CircleAlert, Globe} from 'lucide-react';
import {Alert, AlertDescription} from '@/components/ui/alert';
import {Button} from '@/components/ui/button';
import LeagueCreationDialog from './LeagueCreationDialog';
import {Field, FieldLabel} from '@/components/ui/field';
import {Input} from '@/components/ui/input';
import {useState} from 'react';
import {crearLiga} from './api.js';
import {useNavigate} from 'react-router';
import {routePath, routes} from '@/routes.js';


export default function CrearLiga() {
    const [name, setName] = useState('');
    const [minTeams, setMinTeams] = useState(3);
    const [maxTeams, setMaxTeams] = useState('');
    const [startDateTime, setstartDateTime] = useState('');
    const [roundInterval, setroundInterval] = useState('CONTINUOUS');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const navigate = useNavigate();

    async function handleSubmit(event) {
        event.preventDefault();
        if (isSubmitting) return;

        setError('');
        setSuccess('');
        setIsSubmitting(true);

        try {
            const response = await crearLiga(name, minTeams, maxTeams, startDateTime, roundInterval);
            navigate(routePath(routes.leagueLobby, {id: response.leagueId}), {replace: true});
        } catch (err) {
            const fieldErrors = Object.values(err.fields ?? {}).join(' ');
            setError(fieldErrors || err.message || 'No se pudo crear la liga pública.');
        } finally {
            setIsSubmitting(false);
        }
    }


    return (
        <LeagueCreationDialog title="Crear liga pública" icon={Globe}
            description="Organizá una competencia abierta a otros clubes." busy={isSubmitting}>
            <form onSubmit={handleSubmit} className="grid gap-5 sm:grid-cols-2" aria-busy={isSubmitting}>
                <Field className="sm:col-span-2">
                    <FieldLabel htmlFor="league-name">Nombre de la liga</FieldLabel>
                    <Input
                        id="league-name"
                        type="text"
                        className="h-10"
                        value={name}
                        onChange={(event) => setName(event.target.value)}
                        placeholder="Nombre de la liga"
                        required
                    />
                </Field>
                <Field>
                    <FieldLabel htmlFor="min-teams">Mínimo de clubes</FieldLabel>
                    <Input
                        id="min-teams"
                        type="number"
                        className="h-10"
                        value={minTeams}
                        onChange={(event) => setMinTeams(event.target.value)}
                        min="3"
                        step="1"
                        required
                    />
                </Field>
                <Field>
                    <FieldLabel htmlFor="max-teams">Máximo de clubes</FieldLabel>
                    <Input
                        id="max-teams"
                        type="number"
                        className="h-10"
                        value={maxTeams}
                        onChange={(event) => setMaxTeams(event.target.value)}
                        min={minTeams}
                        step="1"
                        required
                    />
                </Field>
                <Field>
                    <FieldLabel htmlFor="start-date">Fecha y hora de inicio</FieldLabel>
                    <Input
                        id="start-date"
                        type="datetime-local"
                        className="h-10"
                        value={startDateTime}
                        onChange={(event) => setstartDateTime(event.target.value)}
                        required
                    />
                </Field>
                <Field>
                    <FieldLabel htmlFor="round-interval">Frecuencia de rondas</FieldLabel>
                    <select
                        id="round-interval"
                        className="h-10 w-full min-w-0 rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                        value={roundInterval}
                        onChange={(event) => setroundInterval(event.target.value)}
                        required
                    >
                        <option value="CONTINUOUS">Seguidas</option>
                        <option value="DAILY">Diarias</option>
                        <option value="WEEKLY">Semanales</option>
                    </select>
                </Field>

                <div className="space-y-4 border-t pt-5 sm:col-span-2">
                    {error && (
                        <Alert variant="destructive">
                            <CircleAlert aria-hidden="true"/>
                            <AlertDescription>{error}</AlertDescription>
                        </Alert>
                    )}
                    {success && <p role="status" className="text-sm text-primary">{success}</p>}
                    <div className="flex justify-end">
                        <Button type="submit" size="lg" className="w-full sm:w-auto" disabled={isSubmitting}>
                            {isSubmitting ? 'Creando…' : 'Crear liga'}
                        </Button>
                    </div>
                </div>
            </form>
        </LeagueCreationDialog>
    );
}
