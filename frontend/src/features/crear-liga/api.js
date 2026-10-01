import {request} from '@/api/http.js'


export async function crearLiga(name, minTeams, maxTeams, startDate, roundInterval){
    return request('/leagues/public', {
        method: 'POST',
        body: {name, min_teams: Number(minTeams), max_teams: Number(maxTeams), start_date: new Date(startDate), round_interval: roundInterval}
    });
}
