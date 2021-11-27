# JSON Documentation

This md file contains an explanation as to what all the possible keys does for every json file used by the program.

## config_class.json

* ``classname`` - The name of this class.
  * ``health`` - The base health of this class.
  * ``health_giant`` - The base health of the giant version of this class.
  * ``power`` - The base power of this class. Must be greater than 0.
  * ``speed`` - The speed of this class.
  * ``power_mult_skill`` - A list of 4 floats, each corresponding to a multiplier for the skill of a class from easy to expert.
  * ``power_mult_weapon`` - A list of 3 floats, each corresponding to a multiplier for the weapon slot, starting with primary, then secondary, then melee.
  * ``primaries`` - A list of primary weapons that this class is allowed to use.
    * ``name`` - The name of this weapon.
    * ``weight`` - The chance that this weapon will be used relative to others.
    * ``passive`` - Allows this weapon to be used in parallel with another weapon, and will prevent this weapon from being chosen as the main weapon.
    * ``charge`` - Tells the program that this weapon is compatible with Attributes SpawnWithFullCharge
    * ``alt`` - A list of alternate names for this weapon.
  * ``secondaries`` - A list of secondary weapons that this class is allowed to use.
  * ``melee`` - A list of melee weapons that this class is allowed to use.

## config_attributes.json

* ``attribute_defines`` - A list containing all attributes which can be interpreted by the program in some way.
  * ``name`` - The name of this attribute.
  * ``type`` - What value does this attribute modify? Can either be power, endurance or strength
  * ``inverse`` - The name of this attribute when it tends towards 0.
  * ``operator`` - How the value of this attribute acts upon the power, endurance or strength of a bot. Can either be ``exp``, ``inv_exp``, ``mult``, ``add`` or ``none``
  * ``base`` - Base modifier amount.
  * ``mult`` - A multiplier to the base amount.
  * ``clamp`` - Used when calculating the strength of a bot. If the value goes below this amount, then it will get interpreted as this value instead.
  * ``ceil`` - Identical to clamp, except it checks for any value above this amount.
  * ``def`` - The default value of this attribute.
  * ``alt`` - A list of alternate names for this attribute.
  * ``ca`` - If this attribute should be used in CharaterAttributes.
* ``classname`` - The name of this class.
  * ``attributes_primary`` - A list of attributes this class can use for their primary weapons.
    * ``name`` - The name of the referenced attribute.
    * ``min`` - The minimum value this attribute can have.
    * ``max`` - The maximum value this attribute can have.
    * ``step`` - Every possible value between min and max starting from min. Cannot be 0. 
  * ``attributes_secondary`` - A list of attributes this class can use for their primary weapons.
  * ``attributes_melee`` - A list of attributes this class can use for their primary weapons.
  * ``whitelist_primary`` - A list of attribute referenced in ``attributes_primary`` which can be used for primary weapons.
  * ``whitelist_secondary`` - A list of attribute referenced in ``attributes_primary`` which can be used for primary weapons.
  * ``whitelist_melee`` - A list of attribute referenced in ``attributes_primary`` which can be used for primary weapons.
  * ``items`` - A list of items for this class.
    * ``itemname`` - The name of this item.
      * ``default`` - The default attributes of this item.
      * ``whitelist_extend`` - Extend the whitelist of this weapon's slot with another attribute found within the corresponding attributes for this slot.
      * ``whitelist`` - Override the exisitng whitelist for this slot with a new list of attributes.
      * ``priority`` - A list of attribute names which will be chosen first over others when making a tfbot with this weapon.
      * ``power_base`` - Override the base power of a class with this number. Useful for weaker weapons or passive weapons.
      * ``power_mult`` - The final power of a weapon will get multiplied by this value.
      * ``override`` - Override one or multiple attribute potential values. Useful for weapons which need extreme attribute values to make it useful.

## config_waves.json

* ``pattern`` - Contains specific reoccuring rules for waves.
  * ``every`` - This pattern occurs every X wave.
    * ``X`` - The number of this wave.
      * ``conds`` - A set of conditions for this rule to apply.
      * ``rules`` - If the conditions are true, these rules will apply for this wave.
  * ``range`` - A list of conditions applying if the wave number is within a specific range. First index is the start of the range, second index is the end of the range, and the third index are the rules to apply.
* ``individual`` - This rule wipll apply to this specific wave.
  * ``X`` - The number of this wave.
    * ``rules`` - The rules to apply for this wave. 

**conds**
* ``starting_from`` - The number to consider this pattern from.

**rules**
* ``power_mult_max`` - A multiplier to the maxmimum power that bots can have for this wave.
* ``endurance_mult_max`` - A multiplier to the maxmimum edurance that bots can have for this wave.
* ``strength_mult_max`` - A multiplier to the maxmimum strength that bots can have for this wave.
* ``cash_mult_max`` - A multiplier to the cash provided this wave.
* ``power_add`` - The amount of power to add to this wave.
* ``endurance_add`` - The amount of power to add to this wave.
* ``strength_add`` - The amount of power to add to this wave.
* ``cash_add`` - The amount of power to add to this wave.
* ``no`` - A list of bots which cannot be used for this wave. Can contain ``commons``, ``giants``, ``tanks`` or ``boss``.
* ``must_include`` - A list of bots which must be included in this wave, at least once. Can contain ``commons``, ``giants``, ``tanks`` or ``boss``.
* ``subwaves`` - Override the amount of subwaves (groups of identically named wavespawns) which can be used this wave.
* ``bot_amount`` - Amount of total groups each wavespawn will have for the entirety of a wave.
* ``bot_types`` - Amount of wavespawns each subwave will have for the entirety of a wave.
* ``custom_only`` - The program will exclusively create new tfbots instead of opting to use ones found inside its templates.

## config_map.json

* ``name`` - The name of this map.
* ``relay_start`` - The name of the wave start relay for this map.
* ``relay_end`` - The name of the wave end relay for this map.
* ``spawn_common`` - All the possible spawns common robots can use, each with their own weight.
* ``spawn_giant`` - All the possible spawns giant robots can use, each with their own weight.
* ``spawn_tank`` - All the possible spawns tanks can use, each with their own weight.
* ``spawn_boss`` - All the possible spawns boss robots can use, each with their own weight.
* ``length`` - The approximate length of this map.

## config_ai.json

* ``cash_start_min`` - The minimum starting cash this mission can have.
* ``cash_start_max`` - The maximum starting cash this mission can have.
* ``cash_per_min`` - The minimum amount of cash per wave.
* ``cash_per_max`` - The maximum amount of cash per wave.
* ``max_waves`` - The desired amount of waves which will be created for this mission.
* ``max_tfbots`` - The maximum amount of TFBots allowed alive in each subwave group.
* ``bot_attack_spawnroom`` - If bots should be allowed to attack while in spawn.
* ``bot_attribute_threshold`` - The minimum strength required for a custom bot to be allowed to use attributes.
* ``bot_attribute_per`` - Increase the maximum amount of possible attribute per this amount of strength.
* ``bot_attribute_giant_per`` - Identical to ``bot_attribute_per``, but applies to giants instead.
* ``bot_attribute_cap`` - The maximum amount of attributes allowed to be used at once for a single weapon. 
* ``bot_passive_chance`` - When making a new bot, this is the chance that it will be allowed to have a passive weapon. Must be a value between ``0`` and ``1``.
* ``bot_minigiant_chance`` - When making a new bot with a strength above ``bot_hp_threshold``, this is the chance that it will be chosen to be a minigiant.
* ``bot_hp_threshold`` - The minimum strength of a bot to be eligble for minigiant status.
* ``bot_giant_hp_threshold`` - The minimum strength where a giant's bot total strength will be split evenly between endurance and power.
* ``bot_burst_chance`` - The percentage chance from ``0`` to ``1`` that a bot with an eligible weapon will be given HoldFireUntilFullReload.
* ``bot_crit_threshold`` - The minimum strength a bot can have before being given ``Attributes AlwaysCrit``.
* ``bot_crit_chance`` - The percentage chance a bot, if eligible, will be given crits.
* ``bot_deviance_chance`` - The percentage chance an attribute can be deviant.
* ``bot_deviance_max`` - The maximum number of 'deviant' attributes a robot can have.
* ``bot_common_charge_chance`` - The percentage chance a common robot with a chargeable weapon will start with it fully charged.
* ``bot_giant_charge_threshold`` - The strength threshold before a randomly made bot can be given SpawnWithFullCharge.
* ``bot_giant_search_add`` - When searched for eligible templates, this strength will be added to desired search strength. Helps find template giants for lower money waves.
* ``bot_common_chance`` - When making a subwave, this is the weight that a common robot type will be chosen.
* ``bot_giant_chance`` - When making a subwave, this is the weight that a giant robot type will be chosen.
* ``bot_tank_chance`` - When making a subwave, this is the weight that a tank will be chosen.
* ``bot_boss_chance`` - When making a subwave, this is the weight that a boss robot type will be chosen.
* ``bot_boss_strength_mult`` - When determining what boss bot to use, it multiplies the searched strength by this multiplier.
* ``bot_boss_custom_only`` - If only randomly generated bots should be used as bosses.
* ``global_strength_mult`` - The global multiplier to strength when making a mission.
* ``tank_strength_mult`` - The multiplier to individual tank strength when making a wavespawn with them.
* ``tank_strength_bias`` - Decreases tank hp by this inverted percentage amount depending on the number of subwaves. Numbers closer to 1 decrease it more. Negative numbers increase tank hp.
* ``tank_speeds``- The possible speeds a tank can have, each with their own weighted chance.
* ``wavespawn_regular_weight`` - When making a subwave, this is the weight that a regular wavespawn (with only one bot type) will be chosen.
* ``wavespawn_random_weight`` - When making a subwave, this is the weight that RandomChoice will be chosen as the spawner.
* ``wavespawn_squad_weight`` - When making a subwave, this is the weight that Squad will be chosen as the spawner.
* ``wavespawn_squad_max`` - The maximum amount of robots which can be used in a squad.
* ``wavespawn_durations`` - The possible durations a subwave can have, each with their own weighted chance.
* ``wavespawn_ggroup_threshold`` - The minimum strength that giants require before their SpawnCount can exceed 1.
* ``wavespawn_giant_amount`` - The possible amounts of giants in a wavespawn, each with their own weighted chance.
* ``wavespawn_giant_spawn_decrement`` - The rate at which a giant's spawn delay decreases as strength increases.
* ``wavespawn_giant_spawn_shift`` - The amount of strength which a giant's spawn delay reaches half its initial value.
* ``wavespawn_amount`` - The possible amount of wavespawns each subwave can have, each with their own weighted chance.
* ``subwave_amount`` - The possible amount of subwaves each wave can have, each with their own weighted chance.
* ``allow_reoccuring`` - If set to true, allows randomly made bots to be used as templates for future waves.
* ``wave_support_chance`` - The chance that any wave will have mission support, if allowed.
* ``wave_support_strength`` - The base strength value that support bots will have to work with.
* ``wave_support_amount`` - The possible amount of separate support missions that a wave can have, each with their own weighted chance.
* ``wave_support_bot_amount`` - The possible amount of bots that can be used for each support mission, each with their own weighted chance.
* ``wave_strength_growth`` - How fast the exponential curve grows in relation to money. Keep this value very small for good results.
* ``wave_strength_steep`` - A float number which determines where the curve grows.
* ``wave_strength_alt_mult`` - The alternate strength function's multiplier, stacked with the base strength multiplier.
* ``wave_strength_alt_slope`` - The alternate strength function's growth amount. Higher value make the growth significantly slower.
* ``wave_strength_tank_mult`` - The alternate tank strength function's multiplier.
* ``wave_strength_tank_slope`` - The alternate strength function's growth amount. Higher values make the growrth significantly slower.
* ``strength_variance`` - A range of the strength multiplied and divided by this value will be applied to the ideal strength of a subwave. A bot from templates can be chosen from within this range.
* ``endless`` - If set to true, separate waves will instead be merged together instead of split among separate waves.
* ``spaced`` - If set to true, the output file will be properly spaced and lined, instead of being but on 1 massive line.
* ``modded`` - Unused.
 
