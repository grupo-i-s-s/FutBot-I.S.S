BEGIN;

DO $$
DECLARE
    v_user_id INTEGER;
    v_club_name TEXT;
    v_behaviour_id INTEGER;
    v_player_ids INTEGER[];
    v_player_id INTEGER;
    v_player_count INTEGER;
    v_sequence TEXT;
    v_sequence_value BIGINT;
    v_max_club_id INTEGER;
BEGIN
    SELECT name
    INTO v_club_name
    FROM clubs
    WHERE id = 999;

    IF v_club_name IS NULL THEN
        INSERT INTO users (email, password_hash)
        VALUES ('oponente-prueba@local.invalid', '!sin-acceso!')
        ON CONFLICT (email) DO UPDATE
            SET email = EXCLUDED.email
        RETURNING id INTO v_user_id;

        INSERT INTO clubs (id, user_id, name, avatar, friendly_available)
        VALUES (999, v_user_id, 'bot de prueba', 'avatar-01.png', FALSE);
    ELSIF v_club_name <> 'bot de prueba' THEN
        RAISE EXCEPTION
            'El club con id 999 ya existe y no es bot de prueba.';
    END IF;

    SELECT id
    INTO v_behaviour_id
    FROM behaviors
    WHERE club_id = 999
      AND name = 'Equilibrado';

    IF v_behaviour_id IS NULL THEN
        INSERT INTO behaviors (
            club_id, name, description, code, kind, version, validation_status
        )
        VALUES (
            999,
            'Equilibrado',
            'Comportamiento para el oponente de pruebas.',
            $program$from primitives.behaviours import balanced

def decide(observation):
    return balanced(observation)$program$,
            'PLAYER',
            1,
            'VALID'
        )
        RETURNING id INTO v_behaviour_id;
    ELSE
        UPDATE behaviors
        SET description = 'Comportamiento para el oponente de pruebas.',
            code = $program$from primitives.behaviours import balanced

def decide(observation):
    return balanced(observation)$program$,
            kind = 'PLAYER',
            version = 1,
            validation_status = 'VALID',
            is_deleted = FALSE
        WHERE id = v_behaviour_id;
    END IF;

    SELECT array_agg(id ORDER BY id)
    INTO v_player_ids
    FROM players
    WHERE club_id = 999
      AND behavior_id = v_behaviour_id
      AND is_deleted = FALSE;

    v_player_ids := COALESCE(v_player_ids, ARRAY[]::INTEGER[]);
    v_player_count := cardinality(v_player_ids);

    WHILE v_player_count < 6 LOOP
        INSERT INTO players (
            club_id, behavior_id, name,
            power, agility, control, speed, strength
        )
        VALUES (
            999, v_behaviour_id, 'Oponente ' || (v_player_count + 1),
            60, 60, 60, 60, 60
        )
        RETURNING id INTO v_player_id;

        v_player_ids := array_append(v_player_ids, v_player_id);
        v_player_count := v_player_count + 1;
    END LOOP;

    INSERT INTO default_teams (club_id, line_up)
    VALUES (
        999,
        json_build_object(
            'formationId', 1,
            'starters', json_build_array(
                json_build_object('playerId', v_player_ids[1], 'behaviourId', v_behaviour_id),
                json_build_object('playerId', v_player_ids[2], 'behaviourId', v_behaviour_id),
                json_build_object('playerId', v_player_ids[3], 'behaviourId', v_behaviour_id)
            ),
            'substitutes', json_build_array(
                json_build_object('playerId', v_player_ids[4], 'behaviourId', v_behaviour_id),
                json_build_object('playerId', v_player_ids[5], 'behaviourId', v_behaviour_id),
                json_build_object('playerId', v_player_ids[6], 'behaviourId', v_behaviour_id)
            )
        )
    )
    ON CONFLICT (club_id) DO UPDATE
        SET line_up = EXCLUDED.line_up;

    v_sequence := pg_get_serial_sequence('clubs', 'id');
    SELECT MAX(id) INTO v_max_club_id FROM clubs;

    IF v_sequence IS NOT NULL THEN
        EXECUTE format('SELECT last_value FROM %s', v_sequence::regclass)
        INTO v_sequence_value;

        IF v_sequence_value < v_max_club_id THEN
            PERFORM setval(v_sequence::regclass, v_max_club_id, TRUE);
        END IF;
    END IF;
END $$;

COMMIT;