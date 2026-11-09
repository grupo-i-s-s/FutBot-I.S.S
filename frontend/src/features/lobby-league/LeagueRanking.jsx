import {useEffect, useState} from 'react';
import { getLeagueRanking } from './api.js';
import {Alert, AlertDescription} from '@/components/ui/alert';
import {Card, CardContent, CardHeader} from '@/components/ui/card';
import ClubAvatar from '../my-club/components/ClubAvatar';
import {Link} from 'react-router';
import {routePath, routes} from '@/routes.js';

export default function LeagueRanking({leagueId}) {
    const[rankData, setRankData] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const controller = new AbortController();
        setLoading(true);
        setError(null);
        getLeagueRanking(leagueId, controller.signal)
            .then(rank => { if (!controller.signal.aborted) setRankData(rank); })
            .catch(err => { if (!controller.signal.aborted) setError(err); })
            .finally(() => { if (!controller.signal.aborted) setLoading(false); });
        return () => controller.abort();
    }, [leagueId]);

    return (
        <Card>
            <CardHeader><h2 className="text-lg font-bold">Ranking de la Liga</h2></CardHeader>
            <CardContent aria-busy={loading}>
                {loading && <p role="status" className="py-6 text-center text-sm text-muted-foreground">Cargando ranking…</p>}
                {error && <Alert variant="destructive"><AlertDescription>{error.message}</AlertDescription></Alert>}
                {!loading && !error && (rankData.length === 0 ? (
                    <p className="py-6 text-center text-sm text-muted-foreground">Todavía no hay posiciones disponibles.</p>
                ) : (
                    <div className="overflow-x-auto rounded-lg border">
                        <table className="w-full text-center text-sm">
                            <thead className="bg-muted text-muted-foreground">
                                <tr>
                                    <th scope="col" className="p-3">#</th>
                                    <th scope="col" className="min-w-40 p-3 text-left">Club</th>
                                    {['Pts', 'PJ', 'PG', 'PE', 'PP', 'DG'].map(label => <th key={label} scope="col" className="p-3">{label}</th>)}
                                </tr>
                            </thead>
                            <tbody className="divide-y">
                                {rankData.map((club, index) => (
                                    <tr key={club.id} className="hover:bg-muted/50">
                                        <td className="p-3 text-muted-foreground">{index + 1}</td>
                                        <th scope="row" className="p-3 text-left font-medium">
                                            <Link to={routePath(routes.clubProfile, {clubId: club.id})} className="inline-flex items-center gap-3 hover:underline">
                                                <ClubAvatar avatar={club.avatar} clubName={club.nombre} size="md"/>
                                                <span>{club.nombre}</span>
                                            </Link>
                                        </th>
                                        <td className="p-3 font-bold text-primary">{club.puntos}</td>
                                        {[club.pj, club.pg, club.pe, club.pp, club.dg].map((value, stat) => <td key={stat} className="p-3">{value}</td>)}
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                ))}
            </CardContent>
        </Card>
    );
}
