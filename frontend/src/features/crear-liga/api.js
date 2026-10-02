import {request} from '@/api/http.js'


export async function crearLiga(name, type, minTeams, maxTeams, startDateTime, roundInterval){
    return request('/leagues', {
        method: 'POST',
        body: {name, type, min_teams: Number(minTeams), max_teams: Number(maxTeams), start_datetime: new Date(startDateTime), round_interval: roundInterval}
    });
}
