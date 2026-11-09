import { request } from "@/api/http";

export function getGlobalRanking(signal){
    return request('/ranking-global', {signal});
}