import {request} from '@/api/http.js'


export async function crearLigaPrivada(name, password, minTeams, maxTeams, startDate, roundInterval){
    return request('/leagues/private', {
        method: 'POST',
        body: {name, password, min_teams: Number(minTeams), max_teams: Number(maxTeams), start_date: new Date(startDate), round_interval: roundInterval}
    });
}
