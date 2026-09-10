/* Registry of interactive demos, keyed for PageSpec.interactive. */
import type { ComponentType } from 'react';
import RadarDemo from './radar';
import DiffDemo from './diff';
import CoverDemo from './cover';
import { LinkedinDemo, InterviewDemo, NegotiationDemo } from './career';
import { TracksDemo, MentorDemo, WarmPathDemo } from './growth';
import { OfferDemo, GapDemo, JdDemo, AutopsyDemo, StreakDemo } from './win';
import CrewDemo from './crew';

export const DEMO_COMPONENTS: Record<string, ComponentType> = {
  radar: RadarDemo,
  diff: DiffDemo,
  cover: CoverDemo,
  linkedin: LinkedinDemo,
  interview: InterviewDemo,
  negotiation: NegotiationDemo,
  tracks: TracksDemo,
  mentors: MentorDemo,
  warm: WarmPathDemo,
  offers: OfferDemo,
  gaps: GapDemo,
  jd: JdDemo,
  autopsy: AutopsyDemo,
  streaks: StreakDemo,
  crew: CrewDemo,
};

export { default as RadarDemo } from './radar';
