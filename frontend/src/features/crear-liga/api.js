import {request} from '@/api/http.js'


export async function crearLiga(name, minTeams, maxTeams, startDateTime, roundInterval){
    return request('/leagues/public', {
        method: 'POST',
        body: {name, min_teams: Number(minTeams), max_teams: Number(maxTeams), start_date: new Date(startDateTime), round_interval: roundInterval}
    });
}
